import json
from socket import error as SocketError
from tinyrpc.exc import InvalidReplyError

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host


class Gettopo(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Gettopo, self).__init__(*args, **kwargs)

    #@set_ev_cls(event.EventSwitchRequest, MAIN_DISPATCHER)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def get_topology_data(self, ev):

    	switches = get_switch(self, None)
	switch_json = json.dumps([switch.to_dict() for switch in switches],indent=2)

    	links = get_link(self, None)
    	link_json = json.dumps([link.to_dict() for link in links],indent=2)
	
	hosts = get_host(self, None)
	host_json = json.dumps([host.to_dict() for host in hosts if host.port.port_no != 1],indent=2)
	
	data = "{\n\"switch\":" + switch_json + ",\n\"link\":" + link_json + ",\n\"host\":" + host_json + "\n}";

	with open('/var/www/html/SDN/SDN_web/topo_data.json', 'w') as f:
		f.write(data)

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
