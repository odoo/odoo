import socket
from contextlib import closing
import sys
import docker


def list_all_used_ports():
    dclient = docker.from_env()
    containers = dclient.containers.list(all)
    used_ports = [8888] #8888 to be used for DB templates 
    for each in containers:
        port_info =  each.attrs['HostConfig']['PortBindings']
        if port_info and port_info.get('8069/tcp',None):
            used_ports.append(port_info['8069/tcp'][0]['HostPort'])
    return used_ports


def find_me_an_available_port_within(a,b,c):
    ports_in_use = list_all_used_ports()
    ports_in_use.append(str(c))
    for port in range(b, a,-1):
        if str(port) in ports_in_use:
            continue
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            res = sock.connect_ex(('localhost', port))
            if res != 0:
                print(port)
                return True
    print("0")


if __name__ == "__main__":
    find_me_an_available_port_within(int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]))

