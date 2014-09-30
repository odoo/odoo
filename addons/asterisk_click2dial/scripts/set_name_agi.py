#! /usr/bin/python
# -*- encoding: utf-8 -*-
"""
 Name lookup in OpenERP for incoming and outgoing calls with an
 Asterisk IPBX

 This script is designed to be used as an AGI on an Asterisk IPBX...
 BUT I advise you to use a wrapper around this script to control the
 execution time. Why ? Because if the script takes too much time to
 execute or get stucks (in the XML-RPC request for example), then the
 incoming phone call will also get stucks and you will miss a call !
 The simplest solution I found is to use the "timeout" shell command to
 call this script, for example :

 # timeout 2s get_name_agi.py <OPTIONS>

 See my 2 sample wrappers "set_name_incoming_timeout.sh" and
 "set_name_outgoing_timeout.sh"

 It's probably a good idea to create a user in OpenERP dedicated to this task.
 This user only needs to be part of the group "Phone CallerID", which has
 read access on the 'res.partner' and other objects with phone numbers and
 names.

 Note that this script can be used without OpenERP, with just the
 geolocalisation feature : for that, don't use option --server ;
 only use --geoloc

 This script can be used both on incoming and outgoing calls :

 1) INCOMING CALLS
 When executed from the dialplan on an incoming phone call, it will
 lookup in OpenERP's partners and other objects with phone numbers
 (leads, employees, etc...), and, if it finds the phone number, it will
 get the corresponding name of the person and use this name as CallerID
 name for the incoming call.

 Requires the "base_phone" module
 available from https://code.launchpad.net/openerp-asterisk-connector
 for OpenERP version >= 7.0

 Asterisk dialplan example :

 [from-extern]
 exten = _0141981242,1,AGI(/usr/local/bin/set_name_incoming_timeout.sh)
 same = n,Dial(SIP/10, 30)
 same = n,Answer
 same = n,Voicemail(10@default,u)
 same = n,Hangup

 2) OUTGOING CALLS
 When executed from the dialplan on an outgoing call, it will
 lookup in OpenERP the name corresponding to the phone number
 that is called by the user and it will update the name of the
 callee on the screen of the phone of the caller.

 For that, it uses the CONNECTEDLINE dialplan function of Asterisk
 See the following page for more info:
 https://wiki.asterisk.org/wiki/display/AST/Manipulating+Party+ID+Information

 It is not possible to set the CONNECTEDLINE directly from an AGI script,
 (at least not with Asterisk 11) so the AGI script sets a variable
 "connectedlinename" that can then be read from the dialplan and passed
 as parameter to the CONNECTEDLINE function.

 Here is the code that I used on the pre-process subroutine
 "openerp-out-call" of the Outgoing Call of my Xivo server :

 [openerp-out-call]
 exten = s,1,AGI(/var/lib/asterisk/agi-bin/set_name_outgoing_timeout.sh)
 same = n,Set(CONNECTEDLINE(name,i)=${connectedlinename})
 same = n,Set(CONNECTEDLINE(name-pres,i)=allowed)
 same = n,Set(CONNECTEDLINE(num,i)=${XIVO_DSTNUM})
 same = n,Set(CONNECTEDLINE(num-pres)=allowed)
 same = n,Return()

 Of course, you should adapt this example to the Asterisk server you are using.

"""

__author__ = "Alexis de Lattre <alexis.delattre@akretion.com>"
__date__ = "August 2014"
__version__ = "0.5"

#  Copyright (C) 2010-2014 Alexis de Lattre <alexis.delattre@akretion.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xmlrpclib
import sys
from optparse import OptionParser


# Name that will be displayed if there is no match
# and no geolocalisation
not_found_name = "Not in OpenERP"

# Define command line options
options = [
    {'names': ('-s', '--server'), 'dest': 'server', 'type': 'string',
        'action': 'store', 'default': False,
        'help': 'DNS or IP address of the OpenERP server. Default = none '
        '(will not try to connect to OpenERP)'},
    {'names': ('-p', '--port'), 'dest': 'port', 'type': 'int',
        'action': 'store', 'default': 8069,
        'help': "Port of OpenERP's XML-RPC interface. Default = 8069"},
    {'names': ('-e', '--ssl'), 'dest': 'ssl',
        'help': "Use XML-RPC secure i.e. with SSL instead of clear XML-RPC. "
        "Default = no, use clear XML-RPC",
        'action': 'store_true', 'default': False},
    {'names': ('-d', '--database'), 'dest': 'database', 'type': 'string',
        'action': 'store', 'default': 'openerp',
        'help': "OpenERP database name. Default = 'openerp'"},
    {'names': ('-u', '--user-id'), 'dest': 'user', 'type': 'int',
        'action': 'store', 'default': 2,
        'help': "OpenERP user ID to use when connecting to OpenERP. "
        "Default = 2"},
    {'names': ('-w', '--password'), 'dest': 'password', 'type': 'string',
        'action': 'store', 'default': 'demo',
        'help': "Password of the OpenERP user. Default = 'demo'"},
    {'names': ('-a', '--ascii'), 'dest': 'ascii',
        'action': 'store_true', 'default': False,
        'help': "Convert name from UTF-8 to ASCII. Default = no, keep UTF-8"},
    {'names': ('-n', '--notify'), 'dest': 'notify',
        'action': 'store_true', 'default': False,
        'help': "Notify OpenERP users via a pop-up (requires the OpenERP "
        "module 'base_phone_popup'). If you use this option, you must pass "
        "the logins of the OpenERP users to notify as argument to the "
        "script. Default = no"},
    {'names': ('-g', '--geoloc'), 'dest': 'geoloc',
        'action': 'store_true', 'default': False,
        'help': "Try to geolocate phone numbers unknown to OpenERP. This "
        "features requires the 'phonenumbers' Python lib. To install it, "
        "run 'sudo pip install phonenumbers' Default = no"},
    {'names': ('-l', '--geoloc-lang'), 'dest': 'lang', 'type': 'string',
        'action': 'store', 'default': "en",
        'help': "Language in which the name of the country and city name "
        "will be displayed by the geolocalisation database. Use the 2 "
        "letters ISO code of the language. Default = 'en'"},
    {'names': ('-c', '--geoloc-country'), 'dest': 'country', 'type': 'string',
        'action': 'store', 'default': "FR",
        'help': "2 letters ISO code for your country e.g. 'FR' for France. "
        "This will be used by the geolocalisation system to parse the phone "
        "number of the calling party. Default = 'FR'"},
    {'names': ('-o', '--outgoing'), 'dest': 'outgoing',
        'action': 'store_true', 'default': False,
        'help': "Update the Connected Line ID name on outgoing calls via a "
        "call to the Asterisk function CONNECTEDLINE(), instead of updating "
        "the Caller ID name on incoming calls. Default = no."},
    {'names': ('-i', '--outgoing-agi-variable'), 'dest': 'outgoing_agi_var',
        'type': 'string', 'action': 'store', 'default': "extension",
        'help': "Enter the name of the AGI variable (without the 'agi_' "
        "prefix) from which the script will get the phone number dialed by "
        "the user on outgoing calls. For example, with Xivo, you should "
        "specify 'dnid' as the AGI variable. Default = 'extension'"},
    {'names': ('-m', '--max-size'), 'dest': 'max_size', 'type': 'int',
        'action': 'store', 'default': 40,
        'help': "If the name has more characters this maximum size, cut it "
        "to this maximum size. Default = 40"},
]


def stdout_write(string):
    '''Wrapper on sys.stdout.write'''
    sys.stdout.write(string.encode(sys.stdout.encoding or 'utf-8', 'replace'))
    sys.stdout.flush()
    # When we output a command, we get an answer "200 result=1" on stdin
    # Purge stdin to avoid these Asterisk error messages :
    # utils.c ast_carefulwrite: write() returned error: Broken pipe
    sys.stdin.readline()
    return True


def stderr_write(string):
    '''Wrapper on sys.stderr.write'''
    sys.stderr.write(string.encode(sys.stdout.encoding or 'utf-8', 'replace'))
    sys.stdout.flush()
    return True


def geolocate_phone_number(number, my_country_code, lang):
    import phonenumbers
    import phonenumbers.geocoder
    res = ''
    phonenum = phonenumbers.parse(number, my_country_code.upper())
    city = phonenumbers.geocoder.description_for_number(phonenum, lang.lower())
    country_code = phonenumbers.region_code_for_number(phonenum)
    # We don't display the country name when it's my own country
    if country_code == my_country_code.upper():
        if city:
            res = city
    else:
        # Convert country code to country name
        country = phonenumbers.geocoder._region_display_name(
            country_code, lang.lower())
        if country and city:
            res = country + ' ' + city
        elif country and not city:
            res = country
    return res


def convert_to_ascii(my_unicode):
    '''Convert to ascii, with clever management of accents (é -> e, è -> e)'''
    import unicodedata
    if isinstance(my_unicode, unicode):
        my_unicode_with_ascii_chars_only = ''.join((
            char for char in unicodedata.normalize('NFD', my_unicode)
            if unicodedata.category(char) != 'Mn'))
        return str(my_unicode_with_ascii_chars_only)
    # If the argument is already of string type, return it with the same value
    elif isinstance(my_unicode, str):
        return my_unicode
    else:
        return False


def main(options, arguments):
    # print 'options = %s' % options
    # print 'arguments = %s' % arguments

    # AGI passes parameters to the script on standard input
    stdinput = {}
    while 1:
        input_line = sys.stdin.readline()
        if not input_line:
            break
        line = input_line.strip()
        try:
            variable, value = line.split(':')
        except:
            break
        if variable[:4] != 'agi_':  # All AGI parameters start with 'agi_'
            stderr_write("bad stdin variable : %s\n" % variable)
            continue
        variable = variable.strip()
        value = value.strip()
        if variable and value:
            stdinput[variable] = value
    stderr_write("full AGI environnement :\n")

    for variable in stdinput.keys():
        stderr_write("%s = %s\n" % (variable, stdinput.get(variable)))

    if options.outgoing:
        phone_number = stdinput.get('agi_%s' % options.outgoing_agi_var)
        stdout_write('VERBOSE "Dialed phone number is %s"\n' % phone_number)
    else:
        # If we already have a "True" caller ID name
        # i.e. not just digits, but a real name, then we don't try to
        # connect to OpenERP or geoloc, we just keep it
        if (
                stdinput.get('agi_calleridname')
                and not stdinput.get('agi_calleridname').isdigit()
                and stdinput.get('agi_calleridname').lower()
                not in ['asterisk', 'unknown', 'anonymous']
                and not options.notify):
            stdout_write(
                'VERBOSE "Incoming CallerID name is %s"\n'
                % stdinput.get('agi_calleridname'))
            stdout_write(
                'VERBOSE "As it is a real name, we do not change it"\n')
            return True

        phone_number = stdinput.get('agi_callerid')

    stderr_write('stdout encoding = %s\n' % sys.stdout.encoding or 'utf-8')

    if not isinstance(phone_number, str):
        stdout_write('VERBOSE "Phone number is empty"\n')
        exit(0)
    # Match for particular cases and anonymous phone calls
    # To test anonymous call in France, dial 3651 + number
    if not phone_number.isdigit():
        stdout_write(
            'VERBOSE "Phone number (%s) is not a digit"\n' % phone_number)
        exit(0)

    stdout_write('VERBOSE "Phone number = %s"\n' % phone_number)

    res = False
    # Yes, this script can be used without "-s openerp_server" !
    if options.server:
        if options.ssl:
            stdout_write(
                'VERBOSE "Starting XML-RPC secure request on OpenERP %s:%s"\n'
                % (options.server, str(options.port)))
            protocol = 'https'
        else:
            stdout_write(
                'VERBOSE "Starting clear XML-RPC request on OpenERP %s:%s"\n'
                % (options.server, str(options.port)))
            protocol = 'http'

        sock = xmlrpclib.ServerProxy(
            '%s://%s:%s/xmlrpc/object'
            % (protocol, options.server, str(options.port)))

        try:
            if options.notify and arguments:
                res = sock.execute(
                    options.database, options.user, options.password,
                    'phone.common', 'incall_notify_by_login',
                    phone_number, arguments)
                stdout_write('VERBOSE "Calling incall_notify_by_login"\n')
            else:
                res = sock.execute(
                    options.database, options.user, options.password,
                    'phone.common', 'get_name_from_phone_number',
                    phone_number)
                stdout_write('VERBOSE "Calling get_name_from_phone_number"\n')
            stdout_write('VERBOSE "End of XML-RPC request on OpenERP"\n')
            if not res:
                stdout_write('VERBOSE "Phone number not found in OpenERP"\n')
        except:
            stdout_write('VERBOSE "Could not connect to OpenERP"\n')
            res = False
        # To simulate a long execution of the XML-RPC request
        # import time
        # time.sleep(5)

    # Function to limit the size of the name
    if res:
        if len(res) > options.max_size:
            res = res[0:options.max_size]
    elif options.geoloc:
        # if the number is not found in OpenERP, we try to geolocate
        stdout_write(
            'VERBOSE "Trying to geolocate with country %s and lang %s"\n'
            % (options.country, options.lang))
        res = geolocate_phone_number(
            phone_number, options.country, options.lang)
    else:
        # if the number is not found in OpenERP and geoloc is off,
        # we put 'not_found_name' as Name
        res = not_found_name

    # All SIP phones should support UTF-8...
    # but in case you have analog phones over TDM
    # or buggy phones, you should use the command line option --ascii
    if options.ascii:
        res = convert_to_ascii(res)

    stdout_write('VERBOSE "Name = %s"\n' % res)
    if options.outgoing:
        stdout_write('SET VARIABLE connectedlinename "%s"\n' % res)
    else:
        stdout_write('SET CALLERID "%s"<%s>\n' % (res, phone_number))
    return True

if __name__ == '__main__':
    usage = "Usage: get_name_agi.py [options] login1 login2 login3 ..."
    epilog = "Script written by Alexis de Lattre. "
    "Published under the GNU AGPL licence."
    description = "This is an AGI script that sends a query to OpenERP. "
    "It can also be used without OpenERP as to geolocate phone numbers "
    "of incoming calls."
    parser = OptionParser(usage=usage, epilog=epilog, description=description)
    for option in options:
        param = option['names']
        del option['names']
        parser.add_option(*param, **option)
    options, arguments = parser.parse_args()
    sys.argv[:] = arguments
    main(options, arguments)
