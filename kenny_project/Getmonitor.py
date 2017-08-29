import json
import MySQLdb

from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

monitor_time = 5

tx_now = [0 for n in range(0,30)]
tx_last = [0 for n in range(0,30)]
tx_flow = [0 for n in range(0,30)]

rx_now = [0 for n in range(0,30)]
rx_last = [0 for n in range(0,30)]
rx_flow = [0 for n in range(0,30)]

class Getmonitor(simple_switch_13.SimpleSwitch13):

    def __init__(self, *args, **kwargs):
        super(Getmonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

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
        body = ev.msg.body
	flow_first = True
	flow_data = "[\n"

        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):

	    if flow_first == False :
            	flow_data += ","
	    else :
		flow_first=False

	    flow_data += "{\n\"datapath_id\":\"" + str(ev.msg.datapath.id) + "\",\n\"in_port\":\"" + str(stat.match['in_port']) + "\",\n\"eth_dst\":\"" + str(stat.match['eth_dst']) + "\",\n\"port\":\"" + str(stat.instructions[0].actions[0].port) + "\",\n\"packet_count\":\"" + str(stat.packet_count) + "\",\n\"byte_count\":\"" + str(stat.byte_count) + "\"\n}"

	flow_data +="\n]"
	flow_first=True

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

	try:
	    db = MySQLdb.connect(host="localhost", user="root", passwd="root", db="total_flow")
	    cursor = db.cursor()
	    #sql = "INSERT INTO total_flow_data (tx_flow, rx_flow) VALUES ('%d','%d')" % (,)
	    cursor.execute("INSERT INTO total_flow_data (tx_flow, rx_flow) VALUES ('1','2')")
	    db.commit()
	    db.close()
	except MySQLdb.Error as e:
  	    print "Error %d: %s" % (e.args[0], e.args[1])

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
