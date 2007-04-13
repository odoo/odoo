#!/usr/bin/python
# -*- encoding: utf-8 -*-

import re
import smtplib
import email, mimetypes
from email.Header import decode_header
from email.MIMEText import MIMEText
import xmlrpclib
import os
import binascii

email_re = re.compile(r"""
	([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
	@                                # mandatory @ sign
	[a-zA-Z0-9][\w\.-]*              # domain must start with a letter ... Ged> why do we include a 0-9 then?
	 \.
	 [a-z]{2,3}                      # TLD
	)
	""", re.VERBOSE)
project_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)

priorities = {
	'1': '1 (Highest)',
	'2': '2 (High)',
	'3': '3 (Normal)',
	'4': '4 (Low)',
	'5': '5 (Lowest)',
}

class rpc_proxy(object):
	def __init__(self, uid, passwd, host='localhost', port=8069, path='object', dbname='terp'):
		self.rpc = xmlrpclib.ServerProxy('http://%s:%s/%s' % (host, port, path))
		self.user_id = uid
		self.passwd = passwd
		self.dbname = dbname

	def __call__(self, *request):
		print self.dbname, self.user_id, self.passwd
		print request
		return self.rpc.execute(self.dbname, self.user_id, self.passwd, *request)

class email_parser(object):
	def __init__(self, uid, password, section, email, email_default, dbname):
		print '* Email parser'
		self.rpc = rpc_proxy(uid, password, dbname=dbname)
		try:
			self.section_id = int(section)
		except:
			self.section_id = self.rpc('crm.case.section', 'search', [('code','=',section)])[0]
		print 'Section ID', self.section_id
		self.email = email
		self.email_default = email_default
		self.canal_id = False

	def email_get(self, email_from):
		res = email_re.search(email_from)
		return res and res.group(1)

	def partner_get(self, email):
		mail = self.email_get(email)
		adr_ids = self.rpc('res.partner.address', 'search', [('email', '=', mail)])
		if not adr_ids:
			return {}
		adr = self.rpc('res.partner.address', 'read', adr_ids, ['partner_id'])
		return {
			'partner_address_id': adr[0]['id'],
			'partner_id': adr[0]['partner_id'][0]
		}

	def _decode_header(self, s):
		from email.Header import decode_header
		s = decode_header(s)
		return ''.join(map(lambda x:x[0].decode(x[1] or 'ascii', 'replace'), s))

	def msg_new(self, msg):
		message = self.msg_body_get(msg)
		data = {
			'name': self._decode_header(msg['Subject']),
			'description': '> '+message['body'].replace('\n','\n> '),
			'section_id': self.section_id,
			'email_from': self._decode_header(msg['From']),
			'email_cc': self._decode_header(msg['Cc'] or ''),
			'canal_id': self.canal_id,
			'user_id': False
		}
		try:
			data.update(self.partner_get(self._decode_header(msg['From'])))
		except Exception, e:
			print e
		#end try

		id = self.rpc('crm.case', 'create', data)
		attachments = message['attachment']

		for attach in attachments or []:
			data_attach = {
				'name': str(attach),
				'datas':binascii.b2a_base64(str(attachments[attach])),
				'datas_fname': attach,
				'description': 'Mail attachment',
				'res_model': 'crm.case',
				'res_id': id
			}
			self.rpc('ir.attachment', 'create', data_attach)
		#end for

		return id

#	#change the return type format to dictionary
#	{
#		'body':'body part',
#		'attachment':{
#					  	'file_name':'file data',
#					  	'file_name':'file data',
#					  	'file_name':'file data',
#					}
#	}
#	#
	def msg_body_get(self, msg):
		message = {}
		message['body'] = ''
		message['attachment'] = {}
		attachment = message['attachment']
		file_name = 1
		if msg.is_multipart():
			for part in msg.get_payload():
				if part.get_content_maintype()=='application' or part.get_content_maintype()=='image':
					filename = part.get_filename()
					if filename != None:
						attachment[filename] = part.get_payload(decode=1)
					else:
						filename = 'attach_file'+str(file_name)
						file_name += 1
						attachment[filename] = part.get_payload(decode=1)
					#end if
					#attachment[filename] = part.get_payload(decode=1)
#					fp = open(os.path.join('/home/admin/test-src/', filename), 'wb')
#					fp.write(part.get_payload(decode=1))
#					fp.close()
				elif(part.get_content_maintype()=='text') and (part.get_content_subtype()=='plain'):
					message['body'] += part.get_payload(decode=1).decode(part.get_charsets()[0])
				#end if
			#end for
			message['attachment'] = attachment
		else:
			message['body'] = msg.get_payload(decode=1).decode(msg.get_charsets()[0])
			message['attachment'] = None
		return message

	def msg_user(self, msg, id):
		body = self.msg_body_get(msg)
		data = {
			'description': '> '+body['body'].replace('\n','\n> '),
			'email_last': body['body']
		}

		# handle email body commands (ex: Set-State: Draft)
		actions = {}
		for line in body['body'].split('\n'):
			res = command_re.match(line)
			if res:
				actions[res.group(1).lower()] = res.group(2).lower()

		act = 'case_close'
		if 'state' in actions:
			if actions['state'] in ['draft','close','cancel','open','pending']:
				act = 'case_' + actions['state']

		for k1,k2 in [('cost','planned_cost'),('revenue','planned_revenue'),('probability','probability')]:
			try:
				data[k2] = float(actions[k1])
			except:
				pass

		if 'priority' in actions:
			if actions['priority'] in ('1','2','3','4','5'):
				data['priority'] = actions['priority']

		if 'partner' in actions:
			data['email_from'] = actions['partner']

		if 'user' in actions:
			uids = self.rpc('res.users', 'name_search', actions['user'])
			if uids:
				data['user_id'] = uids[0][0]

		self.rpc('crm.case', act, [id])
		self.rpc('crm.case', 'write', [id], data)
		return id

	def msg_send(self, msg, emails, priority=None):
		if not len(emails):
			return False
		del msg['To']
		print '0'
		msg['To'] = emails[0]
		if len(emails)>1:
			if 'Cc' in msg:
				del msg['Cc']
			msg['Cc'] = ','.join(emails[1:])
		msg['Reply-To'] = self.email
		if priority:
			msg['X-Priority'] = priorities.get(priority, '3 (Normal)')
		s = smtplib.SMTP()
		s.connect()
		s.sendmail(self.email, emails, msg.as_string())
		s.close()
		print 'Email Sent To', emails
		return True

	def msg_partner(self, msg, id):
		message = self.msg_body_get(msg)
		body = message['body']
		act = 'case_open'
		self.rpc('crm.case', act, [id])
		body2 = '\n'.join(map(lambda l: '> '+l, (body or '').split('\n')))
		data = {
			'description': body2,
			'email_last': body,
		}
		self.rpc('crm.case', 'write', [id], data)
		return id

	def msg_test(self, msg, case_str):
		if not case_str:
			return (False, False)
		emails = self.rpc('crm.case', 'emails_get', int(case_str))
		return (int(case_str), emails)

	def parse(self, msg):
		case_str = project_re.search(msg.get('Subject', ''))
		(case_id, emails) = self.msg_test(msg, case_str and case_str.group(1))
		if case_id:
			if emails[0] and self.email_get(emails[0])==self.email_get(self._decode_header(msg['From'])):
				print 'From User', case_id
				self.msg_user(msg, case_id)
			else:
				print 'From Partner', case_id
				self.msg_partner(msg, case_id)
		else:
			case_id = self.msg_new(msg)
			subject = self._decode_header(msg['subject'])
			if msg.get('Subject', ''):
				del msg['Subject']
			msg['Subject'] = '['+str(case_id)+'] '+subject
			print 'Case', case_id, 'created...'

		emails = self.rpc('crm.case', 'emails_get', case_id)
		priority = emails[3]
		em = [emails[0], emails[1]] + (emails[2] or '').split(',')
		emails = map(self.email_get, filter(None, em))

		mm = [self._decode_header(msg['From']), self._decode_header(msg['To'])]+self._decode_header(msg.get('Cc','')).split(',')
		msg_mails = map(self.email_get, filter(None, mm))

		emails = filter(lambda m: m and m not in msg_mails, emails)
		self.msg_send(msg, emails, priority)
		try:
			pass
		except:
			print 'Sending mail to default address', self.email_default
			if self.email_default:
				a = self._decode_header(msg['Subject'])
				del msg['Subject']
				msg['Subject'] = '[TinyERP-CaseError] ' + a
				self.msg_send(msg, self.email_default.split(','))
		return emails

if __name__ == '__main__':
	import sys, optparse
	parser = optparse.OptionParser(
		usage='usage: %prog [options]',
		version='%prog v1.0')

	group = optparse.OptionGroup(parser, "Note",
		"This program parse a mail from standard input and communicate "
		"with the Tiny ERP server for case management in the CRM module.")
	parser.add_option_group(group)

	parser.add_option("-u", "--user", dest="userid", help="ID of the user in Tiny ERP", default=3, type='int')
	parser.add_option("-p", "--password", dest="password", help="Password of the user in Tiny ERP", default='admin')
	parser.add_option("-e", "--email", dest="email", help="Email address used in the From field of outgoing messages")
	parser.add_option("-s", "--section", dest="section", help="ID or code of the case section", default="support")
	parser.add_option("-m", "--default", dest="default", help="Default eMail in case of any trouble.", default=None)
	parser.add_option("-d", "--dbname", dest="dbname", help="Database name (default: terp)", default='terp')

	(options, args) = parser.parse_args()
	parser = email_parser(options.userid, options.password, options.section, options.email, options.default, dbname=options.dbname)
	msg_txt = email.message_from_file(sys.stdin)

	#fp = open('/home/admin/Desktop/email1.eml')
	#msg_txt = email.message_from_file(fp)
	#fp.close()

	print 'Mail Sent to ', parser.parse(msg_txt)

