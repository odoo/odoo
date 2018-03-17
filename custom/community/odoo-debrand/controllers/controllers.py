# -*- coding: utf-8 -*-
import imghdr
import json
import functools
from odoo import http, tools
import odoo, os, sys, jinja2
from odoo.addons.web.controllers.main import Database
from odoo.addons.web.controllers import main
from odoo.addons.web.controllers.main import Binary
from odoo.modules import get_resource_path
from cStringIO import StringIO
from odoo.http import request

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.odoo-debrand', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb


class BinaryCustom(Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none")
    def company_logo(self, dbname=None, **kw):
		imgname = 'logo'
		imgext = '.png'
		company_logo = request.env['website'].sudo().search([])[0].company_logo
		custom_logo = tools.image_resize_image(company_logo, (150, None))
		placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
		uid = None
		if request.session.db:
			dbname = request.session.db
			uid = request.session.uid
		elif dbname is None:
			dbname = db_monodb()

		if not uid:
			uid = odoo.SUPERUSER_ID

		if not dbname:
			response = http.send_file(placeholder(imgname + imgext))
		else:
			try:
				# create an empty registry
				registry = odoo.modules.registry.Registry(dbname)
				if custom_logo:
					image_base64 = custom_logo.decode('base64')
					image_data = StringIO(image_base64)
					imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
					response = http.send_file(image_data, filename=imgname + imgext, mtime=None)
				else:
					with registry.cursor() as cr:
						cr.execute("""SELECT c.logo_web, c.write_date
										FROM res_users u
								   LEFT JOIN res_company c
										  ON c.id = u.company_id
									   WHERE u.id = %s
								   """, (uid,))
						row = cr.fetchone()
						if row and row[0]:
							image_base64 = str(row[0]).decode('base64')
							image_data = StringIO(image_base64)
							imgext = '.' + (imghdr.what(None, h=image_base64) or 'png')
							response = http.send_file(image_data, filename=imgname + imgext, mtime=row[1])
						else:
							response = http.send_file(placeholder('nologo.png'))
			except Exception:
				response = http.send_file(placeholder(imgname + imgext))
		return response


class OdooDebrand(Database):
	def _render_template(self, **d):
		d.setdefault('manage', True)
		d['insecure'] = odoo.tools.config['admin_passwd'] == 'admin'
		d['list_db'] = odoo.tools.config['list_db']
		d['langs'] = odoo.service.db.exp_list_lang()
		d['countries'] = odoo.service.db.exp_list_countries()
		website_id = request.env['website'].sudo().search([])
		d['company_name'] = website_id and website_id[0].company_name
		d['favicon_url'] = website_id and website_id[0].favicon_url or ''
		d['company_logo_url'] = website_id and website_id[0].company_logo_url or ''
		# databases list
		d['databases'] = []
		try:
				d['databases'] = http.db_list()
		except odoo.exceptions.AccessDenied:
				monodb = db_monodb()
				if monodb:
						d['databases'] = [monodb]
		return env.get_template("database_manager_extend.html").render(d)
