import os
import socket as _s
import threading as _th                              # should probably use the http.server module. it'll be a lot easier
import mimetypes as _mt
from datetime import datetime as _dt, timezone

num_access      = {}
num_access_lock = _th.Lock()
# Creating a server socket with soket_family AF_INET and socket_type SOCK_STREAM
# since it is TCP i'm using SOCK_STREAM. for UDP use SOCK_DGRAM. the protocol is defaulted to 0(3rd parameter).
server_socket   = _s.socket(_s.AF_INET, _s.SOCK_STREAM)

# bind(): assigning localhost ip address and an arbitrary port number to the created socket object.
# remember to use big number for port. as ports 0 - 1024 are preserved ports for priviledged use
host = ''                                    # '' represents reachable by any address. '127.0.0.1'/'localhost' indicates only the through localhost
port = 0                            # make dynamic
server_socket.bind((host, port))
host_name   = _s.gethostname()
host_ip     = _s.gethostbyname(host_name)
print ("\nThe http server is running on host : {} with ip : {} and port no: {}.".format(host_name, host_ip, server_socket.getsockname()[1]), end='\n\n')
# queues upto 5 requests. argument is 'backlog'.
server_socket.listen(5)

# function to handle the requests from clients
def http_response(client, address):
    ''' A per thread functon which prepares appropriate HTTP response for the GET requests from clients. '''
    message     = client.recv(1024).decode('utf-8')

    if message:
        # convert byte stream to string first for string manipulations. GET request has header only.
        # just type casting to str won't work hence use decode instead. it removes the leading b (byte stream -> "b'.......'")
        in_header   = message.split('\n')
        file_name   = (message.split()[1]).lstrip('/')
        with num_access_lock:
            try:
                n_access= num_access[file_name]                                     # no. of times a file was accessed
            except KeyError:
                n_access                = 1
                num_access[file_name]   = 1
            finally:
                num_access[file_name]   += 1

        file_name       = os.path.join('www', file_name)
        try:
            with open(file_name, 'rb') as r_file:
                res_body   = r_file.read()
        except FileNotFoundError:
            # Send 404 file not found error
            res_status  = in_header[0].split()[-1]+" 404 Not Found"+'\n\n'
            file_name   = os.path.join('www', '_404_error.html')
            with open(file_name, 'rb') as er_file:
                res_body   = er_file.read()
            client.send(res_status.encode('utf-8'))
            client.send(res_body)
            client.close()
            exit(1)                                            # exits the thread only not the whole program

        last_mod    = _dt.fromtimestamp(os.path.getmtime(file_name))  # getmtime() throughs error if file is not accessible. use try catch block

        try:
            content_type = _mt.guess_type(file_name)[0]
        except TypeError:
            content_type = 'application/octet-stream'
        finally:
            if content_type == None:
                content_type = 'application/octet-stream'

        res_status  = in_header[0].split()[-1]+" 200 OK"+'\n'                          # status line
        #print("\n\n this is the first line : \n {}".format(res_header))
        res_date    = _dt.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %Z')
        res_length  = os.path.getsize(file_name)                                    # -25 for extra was being sent
        header_cont = 'Date'+':'+' '+res_date+'\n'
        header_cont = header_cont+'Server'+':'+' '+'Kaizoku Ou'+'\n'
        header_cont = header_cont+'Last-Modified'+':'+' '+last_mod.strftime('%a, %d %b %Y %H:%M:%S %Z')+'\n'
        header_cont = header_cont+'Content-Type'+':'+' '+content_type+'\n'
        header_cont = header_cont+'Content-Length'+':'+' '+str(res_length)+'\n'

        # Unlike in django dictionary can not be passed. the res_body, header, ststus line all should be string
        # that is encoded. used utf-8 //see what others are permitted.
        res_header  = header_cont+'\n'
        client.sendall(res_status.encode('utf-8'))
        client.sendall(res_header.encode('utf-8'))
        while True:
            try:
                client.sendall(res_body)
            except:
                break
        # instead of using getpeername(), the ip and port no. can be sent as args to the thread.
        # client.getpeername() won't work with wget as connection is closed after response
        print('{}|{}|{}|{}\n'.format(file_name[3:], address[0], address[1], n_access))
        client.close()

while True:
    # accept() returns socket object created in server for handling request from client
    # and the address of client requesting. address is nothing but ('hostname', port_number)
    client, address = server_socket.accept()
    print("Client connected with ip : {} and port no. : {}\n".format(address[0], address[1]))

    # if /www/ directory is not found quits the whole program
    if 'www' not in os.listdir(os.getcwd()):
        print("The 'www' directory doesn't exist. \n Serever shutting down......\n")
        #server_socket.shutdown(_s.SHUT_RDWR)        #check for errors
        client.close()
        server_socket.close()
        exit(1)

    th  = _th.Thread(target=http_response, args=(client, address))
    th.start()

# always remember to close the server socket. recommendation is to use
# server_socket.shutdown()  # before close() so that client gets notified of connection closing
#server_socket.shutdown(_s.SHUT_RDWR)
server_socket.close()
