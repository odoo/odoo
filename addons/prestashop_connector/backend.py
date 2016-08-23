import openerp.addons.connector.backend as backend


prestashop = backend.Backend('prestashop')
prestashop1609 = backend.Backend(parent=prestashop, version='1.6')
prestashop1500 = backend.Backend(parent=prestashop, version='1.5')