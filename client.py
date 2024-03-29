from socket import socket, AF_INET, SOCK_STREAM, error as SocketError
from typing import Tuple, Optional, Dict
import hashlib

import helper

REQUEST_CODE_NAMES = """1 - List all albums
2 - List album song
3 - Length of song
4 - Lyrics of song
5 - Get album of song
6 - Search song by name
7 - Search song by lyrics
8 - Quit """

#   Missing requests codes do not hold data
REQUEST_CODE_PROMPTS = {
    2: 'Choose an album: ',
    3: 'Choose a song: ',
    4: 'Choose a song: ',
    5: 'Choose a song: ',
    6: 'Choose a word to search: ',
    7: 'Choose a a word to search: ',
}

PASSWORD = 'Pink Floyd'

logged_user = None


def encrypt_password(password: str) -> str:
    return hashlib.pbkdf2_hmac('sha256',
                               password.encode(),
                               b'de71446e074cb947baf6',
                               31703).hex()


def get_response(sock: socket, request: bytes) -> Optional[Dict[str, str]]:
    """ Gets the response of the server to a request.
    :param sock: The socket connected to the server
    :param request: The request.
    :return: The reply from the server as a string
             If disconnected, returns None.
    """
    try:
        sock.send(request)
        response = sock.recv(1025)

    except SocketError:
        return None

    else:
        return helper.parse_message(response)


def connect_to_server() -> Tuple[socket, str]:
    """ Opens a conversation with the server
    :return: A socket with the server and the server's welcome message
    :throws: SocketError
    """
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(helper.SERVER_ADDR)

    welcome_msg = helper.parse_message(sock.recv(1024))['data']

    return sock, welcome_msg


def get_user_number(min: int, max: int) -> int:
    """ Gets a number from the user between a certain range.
    :param min: inclusive minimum value.
    :param min: inclusive maximum value.
    :return: The number choosen by the user.
    """
    res = None
    try:
        res = int(input('Choose an option: '))
    except ValueError:
        pass
    if res is not None and min <= res <= max:
        return res
    print('Please enter a valid number between {} and {}'.format(min, max))
    return get_user_number(min, max)


def do_user_login(sock: socket):
    # user_password = ''
    # while user_password != PASSWORD:
    #     user_password = input('Enter the password: ')
    global logged_user
    if logged_user is not None:
        sign_out = input('You are already logged in as {}. '
                         'Would you like to sign out? y/n: '
                         .format(logged_user[0]))
        if sign_out == 'y':
            logged_user = None
        else:
            msg = helper.make_message(username=logged_user[0],
                                      password=logged_user[1])

    if logged_user is None:
        if input('Do you have an account on our server? y/n: ') == 'y':
            username = input('Enter your username: ')
            password = input('Enter your password: ')
            password = encrypt_password(password)
            msg = helper.make_message(username=username, password=password)
        else:
            proceed = 'n'
            while proceed != 'y':
                print("Let's create an account.")
                username = input('New acount username: ')
                password = input('New acount password: ')
                print('You are going to create an account '
                      'named {} with password {}'.format(username, password))
                password = encrypt_password(password)
                proceed = input('Are you sure you want to proceed? y/n: ')
                if proceed == 'y':
                    msg = helper.make_message(username=username,
                                              password=password,
                                              new_user='')
    logged_user = (username, password)
    sock.send(msg)
    response = helper.parse_message(sock.recv(1024))
    if 'login_successful' not in response:
        print(format_msg(response))
        logged_user = None
        do_user_login(sock)


def format_msg(message: Dict[str, str]) -> str:
    """ Takes a dictionary that repressents the server's message (such
        as returned by helper.parse_message or make_message) and turn it into a
        human readable string depending on it's fields.
    :param message: The server's message.
                    Entries in the dict are fields of the message.
    :return: A human readable string.
    """
    if 'error' in message:
        return ('An error has uccoured. '
                'Please try again. '
                'Are you using an official client?'
                if message['error'] == 'checksumerror'
                else message['error'])
    elif 'data' in message:
        return message['data']
    else:
        return 'Unknown message format: \n{}'.format(message)


def do_request_response(sock: socket, req_code: int, req_data: str) -> bool:
    """ Prints the result of the request to the user.
    :param sock: The connection to the server
    :param req_code: The request code
    :param req_data: The data field of the request
    :return: True if succesful, False if connection error
    """
    request = helper.make_message(code=req_code, data=req_data)
    response = get_response(sock, request)

    if response is None:
        return False

    print(format_msg(response))
    print('')
    return True


def make_requests_to_server(sock: socket) -> bool:
    """ Makes consecetive requests until disconnected.
    :param sock: Socket to the server
    :return: True if successful, False if connection error
    """
    while True:
        print(REQUEST_CODE_NAMES)
        req_code = get_user_number(1, 8)

        #   If the request code requires data, ask for it
        req_data = ''
        if req_code in REQUEST_CODE_PROMPTS:
            req_data = input(REQUEST_CODE_PROMPTS[int(req_code)])

        success = do_request_response(sock, req_code, req_data)
        if not success:
            return False

        if helper.is_exit_request_code(req_code):
            return True


def ask_for_reconnect() -> bool:
    reconnect = input('Would you like to try reconnecting? y/n: ')
    return reconnect == 'y'


def start_conversation() -> None:
    print('Connecting to server...', end='')
    try:
        sock, welcome_msg = connect_to_server()
    except SocketError:
        print('failure! \n\n')
        print('Cannot connect to server. '
              'Check your internet connection. '
              'Please try again.')
        if ask_for_reconnect():
            start_conversation()
    else:
        with sock:
            print('connected! \n\n')
            print(welcome_msg)

            do_user_login(sock)

            success = make_requests_to_server(sock)
            if not success:
                print('Oops! It seams you were disconnected. '
                      'Check your internet connection.')
                if ask_for_reconnect():
                    start_conversation()


def main():
    start_conversation()


if __name__ == '__main__':
    main()
