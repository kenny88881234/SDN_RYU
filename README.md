# SDN_RYU

conrtoller：
1.安裝RYU
2.下載此程式碼
3.進到ryu/ryu/app
4.執行程式：ryu-manager --verbose rest_qos.py qos_simple_switch_13.py rest_conf_switch.py ~/SDN_RYU/kenny_project/Getmonitor.py ~/SDN_RYU/kenny_project/Gettopo.py (qos_simple_switch_13.py依照RYU book QoS章節建置)

switch(AC1750)：
1.刷入openwrt(openwrt-ar71xx-generic-archer-c7-v2-squashfs-factory.bin)
2.修改network設定：

config interface 'loopback'
        option ifname 'lo'
        option proto 'static'
        option ipaddr '127.0.0.1'
        option netmask '255.0.0.0'

config globals 'globals'
        option ula_prefix 'fd73:a0b4:1a89::/48'

config switch
        option name 'switch0'
        option reset '1'
        option enable_vlan '1'
        option enable_learning '0'

config switch_vlan
        option device 'switch0'
        option vlan '1'
        option ports '1 0t'

config switch_vlan
        option device 'switch0'
        option vlan '2'
        option ports '2 0t'

config switch_vlan
        option device 'switch0'
        option vlan '3'
        option ports '3 0t'

config switch_vlan
        option device 'switch0'
        option vlan '4'
        option ports '4 0t'

config switch_vlan
        option device 'switch0'
        option vlan '5'
        option ports '5 0t'

config interface 'port0'
        option ifname 'eth1.1'
        option proto 'static'

config interface 'port1'
        option ifname 'eth1.2'
        option proto 'static'

config interface 'port2'
        option ifname 'eth1.3'
        option proto 'static'

config interface 'port3'
        option ifname 'eth1.4'
        option proto 'static'

config interface 'port4'
        option ifname 'eth1.5'
        option proto 'static'
        option ipaddr '192.168.1.1'
        option netmask '255.255.255.0'
        
3.ovs-vsctl add-br odin_1 ...etc(投影片裡有)
4.安裝TC套件(QoS應用需要)
