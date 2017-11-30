import json
import MySQLdb
import numpy
import time
import subprocess,sys

from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib import ofctl_v1_3
from ryu.ofproto import ofproto_v1_3

monitor_time = 5

tx_now = [0 for n in range(0,30)]
tx_last = [0 for n in range(0,30)]
tx_flow = [0 for n in range(0,30)]

rx_now = [0 for n in range(0,30)]
rx_last = [0 for n in range(0,30)]
rx_flow = [0 for n in range(0,30)]

total_tx = numpy.zeros((3,5),int)
total_rx = numpy.zeros((3,5),int)
old_tx = numpy.zeros((3,5),int)
old_rx = numpy.zeros((3,5),int)
yesterday_tx = numpy.zeros((3,5),int)
yesterday_rx = numpy.zeros((3,5),int)
limit_flag = numpy.zeros((3,5),int)
to_zero = False

time_data = time.strftime("%Y-%m-%d")

class Getmonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Getmonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
	with open('/var/www/html/SDN/SDN_web/everydaylimit.json','r') as load_f:
            load_dict = json.load(load_f)
	for i in range (1, 2) :
            for j in range (2, 5) :
	        if str(i) in load_dict and str(j-1) in load_dict[str(i)] :
		    load_dict[str(i)][str(j-1)]['flag'] = '0'
	with open('/var/www/html/SDN/SDN_web/everydaylimit.json','w') as limit:
	    json.dump(load_dict,limit)
	db = MySQLdb.connect(host="localhost", user="root", passwd="root", db="total_flow")
        cursor = db.cursor()
	sql = "TRUNCATE total_flow_data"
        cursor.execute(sql)
	db.commit()
        db.close()

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
	global monitor_time
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(monitor_time)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
	global time_data, total_tx, total_rx, old_tx, old_rx, to_zero, yesterday_tx, yesterday_rx, limit_flag
        tx = numpy.zeros((3,5),int)
	rx = numpy.zeros((3,5),int)
	body = ev.msg.body
	flow_first = True
	flow_data = "[\n"
	ip = []
	for i in range (0, 3) :
	    new = []
    	    for j in range (0, 5) :
        	new.append('0')
    	    ip.append(new)

	with open('/var/www/html/SDN/SDN_web/everydaylimit.json','r') as load_f:
            load_dict = json.load(load_f)
	with open('/var/www/html/SDN/SDN_web/topo_data.json','r') as topo_f:
	    topo = json.load(topo_f)
	for i in range(0,len(topo['host'])) :
		ip[int(topo['host'][i]['port']['dpid'])][int(topo['host'][i]['port']['port_no'])] = topo['host'][i]['ipv4'][0]

	db = MySQLdb.connect(host="localhost", user="root", passwd="root", db="total_flow")
        cursor = db.cursor()

        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):

	    if flow_first == False :
            	flow_data += ","
	    else :
		flow_first=False

	    if (stat.instructions[0].actions[0].port > 1) and (stat.instructions[0].actions[0].port < 5) :
	    	tx[ev.msg.datapath.id][stat.instructions[0].actions[0].port] += stat.byte_count
	    if (stat.match['in_port'] > 1) and (stat.match['in_port'] < 5) :
	         rx[ev.msg.datapath.id][stat.match['in_port']] += stat.byte_count

	    flow_data += "{\n\"datapath_id\":\"" + str(ev.msg.datapath.id) + "\",\n\"in_port\":\"" + str(stat.match['in_port']) + "\",\n\"eth_dst\":\"" + str(stat.match['eth_dst']) + "\",\n\"port\":\"" + str(stat.instructions[0].actions[0].port) + "\",\n\"packet_count\":\"" + str(stat.packet_count) + "\",\n\"byte_count\":\"" + str(stat.byte_count) + "\"\n}"

	flow_data +="\n]"
	flow_first=True

	for i in range (1, 2) :
            for j in range (2, 5) :
		if to_zero == True :
		    to_zero = False
		    break;
		if tx[i][j] < old_tx[i][j] or rx[i][j] < old_rx[i][j] :
		    to_zero = True
		    break;
	    if to_zero == True :
		break;

	for i in range (1, 2) :
	    for j in range (2, 5) :
		if to_zero == False :
		    sql = "INSERT INTO total_flow_data (dpid, port_no, tx_flow, rx_flow) VALUES ('%d', '%d', '%d', '%d')" % (i, j, total_tx[i][j] + tx[i][j] - yesterday_tx[i][j], total_rx[i][j] + rx[i][j] - yesterday_rx[i][j])
                    cursor.execute(sql)
		    if str(i) in load_dict and str(j-1) in load_dict[str(i)] :
			flow_str=str(total_tx[i][j] + tx[i][j] - yesterday_tx[i][j] + total_rx[i][j] + rx[i][j] - yesterday_rx[i][j])
			if len(flow_str) == 10 :
			    flow_num=float(flow_str[0]+'.'+flow_str[1])
			if len(flow_str) == 9 :
			    flow_num=float('0.'+flow_str[0])
			if len(flow_str) <= 8 :
			    flow_num=0
			print(flow_num)
			if float(load_dict[str(i)][str(j-1)]['limit']) != 0.0 :
		    	    if float(load_dict[str(i)][str(j-1)]['limit']) <= flow_num :
			    	if load_dict[str(i)][str(j-1)]['flag'] == '0' :
		            	    cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "'+load_dict[str(i)][str(j-1)]['limitnum']+'"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
			    	    subprocess.call(cmd , shell=True)
				    load_dict[str(i)][str(j-1)]['flag'] = '1'
			    else :
			    	if load_dict[str(i)][str(j-1)]['flag'] == '1' :
                                    cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "0"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
                                    subprocess.call(cmd , shell=True)
                                    load_dict[str(i)][str(j-1)]['flag'] = '0'
			else :
			    if load_dict[str(i)][str(j-1)]['flag'] == '1' :
                                cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "0"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
                                subprocess.call(cmd , shell=True)
                                load_dict[str(i)][str(j-1)]['flag'] = '0'
		else :
		    total_tx[i][j] += old_tx[i][j]
		    total_rx[i][j] += old_rx[i][j]
		    sql = "INSERT INTO total_flow_data (dpid, port_no, tx_flow, rx_flow) VALUES ('%d', '%d', '%d', '%d')" % (i, j, total_tx[i][j] - yesterday_tx[i][j], total_rx[i][j] - yesterday_rx[i][j])
            	    cursor.execute(sql)
		    if str(i) in load_dict and str(j-1) in load_dict[str(i)] :
                        flow_str=str(total_tx[i][j] + tx[i][j] - yesterday_tx[i][j] + total_rx[i][j] + rx[i][j] - yesterday_rx[i][j])
                        if len(flow_str) == 10 :
                            flow_num=float(flow_str[0]+'.'+flow_str[1])
                        if len(flow_str) == 9 :
                            flow_num=float('0.'+flow_str[0])
                        if len(flow_str) <= 8 :
                            flow_num=0
                        print(flow_num)
                        if float(load_dict[str(i)][str(j-1)]['limit']) != 0.0 :
                            if float(load_dict[str(i)][str(j-1)]['limit']) <= flow_num :
                                if load_dict[str(i)][str(j-1)]['flag'] == '0' :
                                    cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "'+load_dict[str(i)][str(j-1)]['limitnum']+'"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
                                    subprocess.call(cmd , shell=True)
                                    load_dict[str(i)][str(j-1)]['flag'] = '1'
                            else :
                                if load_dict[str(i)][str(j-1)]['flag'] == '1' :
                                    cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "0"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
                                    subprocess.call(cmd , shell=True)
                                    load_dict[str(i)][str(j-1)]['flag'] = '0'
                        else :
                            if load_dict[str(i)][str(j-1)]['flag'] == '1' :
                                cmd = 'curl -X POST -d '+"'"+'{"priority": "2","match": {"nw_dst": "'+ip[i][j]+'"}, "actions":{"queue": "0"}}'+"'"+' http://localhost:8080/qos/rules/000000000000000'+str(i)
                                subprocess.call(cmd , shell=True)
                                load_dict[str(i)][str(j-1)]['flag'] = '0'

		old_tx[i][j] = tx[i][j]
		old_rx[i][j] = rx[i][j]

	if time_data != time.strftime("%Y-%m-%d") :
	    sql = "TRUNCATE total_flow_data"
	    cursor.execute(sql)

	    for i in range (1, 2) :
                for j in range (2, 5) :
		    if to_zero == False :
			yesterday_tx[i][j] = total_tx[i][j] + tx[i][j]
			yesterday_rx[i][j] = total_rx[i][j] + rx[i][j]
		    else :
			yesterday_tx[i][j] = total_tx[i][j]
			yesterday_rx[i][j] = total_rx[i][j]
		    total_tx[i][j] = 0
		    total_rx[i][j] = 0
		    old_tx[i][j] = 0
		    old_rx[i][j] = 0

	time_data = time.strftime("%Y-%m-%d")
	print(time_data)

	db.commit()
        db.close()

	with open('/var/www/html/SDN/SDN_web/everydaylimit.json','w') as limit:
            json.dump(load_dict,limit)
	with open('/var/www/html/SDN/SDN_web/monitor_flow_data.json', 'w') as f:
		f.write(flow_data)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        global monitor_time
	body = ev.msg.body
	port_first = True
	port_data = "[\n"

        for stat in sorted(body, key=attrgetter('port_no')):

	    if stat.port_no <= 6 :
                num = stat.port_no
            self.change_tx_now(num,stat.tx_bytes)
            self.change_tx_flow(num,tx_now[num]-tx_last[num])
            self.change_tx_flow(num,tx_flow[num]*8/monitor_time)
            self.change_tx_last(num,tx_now[num])

	    self.change_rx_now(num,stat.rx_bytes)
            self.change_rx_flow(num,rx_now[num]-rx_last[num])
            self.change_rx_flow(num,rx_flow[num]*8/monitor_time)
            self.change_rx_last(num,rx_now[num])

	    if stat.port_no <= 6 :
	    	if port_first == False :
            	    port_data += ","
	    	else :
		    port_first=False

	        port_data += "{\n\"datapath_id\":\"" + str(ev.msg.datapath.id) + "\",\n\"port_no\":\"" + str(stat.port_no) + "\",\n\"rx_packets\":\"" + str(stat.rx_packets) + "\",\n\"rx_bytes\":\"" + str(stat.rx_bytes) + "\",\n\"rx_errors\":\"" + str(stat.rx_errors) + "\",\n\"tx_packets\":\"" + str(stat.tx_packets) + "\",\n\"tx_bytes\":\"" + str(stat.tx_bytes) + "\",\n\"tx_errors\":\"" + str(stat.tx_errors) + "\",\n\"tx_flow\":\"" + str(tx_flow[num]) + "\",\n\"rx_flow\":\"" + str(rx_flow[num]) + "\"\n}"

	port_data +="\n]"
	port_first=True

	with open('/var/www/html/SDN/SDN_web/monitor_port_data.json', 'w') as f:
		f.write(port_data)
    def change_tx_now(self,num1,num2):
        global tx_now
        tx_now[num1] = num2
    def change_tx_last(self,num1,num2):
        global tx_last
        tx_last[num1] = num2
    def change_tx_flow(self,num1,num2):
        global tx_flow
        tx_flow[num1] = num2
    def change_rx_now(self,num1,num2):
        global rx_now
        rx_now[num1] = num2
    def change_rx_last(self,num1,num2):
        global rx_last
        rx_last[num1] = num2
    def change_rx_flow(self,num1,num2):
        global rx_flow
        rx_flow[num1] = num2

#                                                    __----~~~~~~~~~~~------___
#                                   .  .   ~~//====......          __--~ ~~
#                   -.            \_|//     |||\\  ~~~~~~::::... /~
#                ___-==_       _-~o~  \/    |||  \\            _/~~-
#        __---~~~.==~||\=_    -_--~/_-~|-   |\\   \\        _/~
#    _-~~     .=~    |  \\-_    '-~7  /-   /  ||    \      /
#  .~       .~       |   \\ -_    /  /-   /   ||      \   /
# /  ____  /         |     \\ ~-_/  /|- _/   .||       \ /
# |~~    ~~|--~~~~--_ \     ~==-/   | \~--===~~        .\
#          '         ~-|      /|    |-~\~~       __--~~
#                      |-~~-_/ |    |   ~\_   _-~            /\
#                           /  \     \__   \/~                \__
#                       _--~ _/ | .-~~____--~-/                  ~~==.
#                      ((->/~   '.|||' -_|    ~~-/ ,              . _||
#                                 -_     ~\      ~~---l__i__i__i--~~_/
#                                 _-~-__   ~)  \--______________--~~
#                               //.-~~~-~_--~- |-------~~~~~~~~
#                                      //.-~~~--\
#                   fuck Bug
