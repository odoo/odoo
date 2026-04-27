# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import SpreadsheetTestCommon
from odoo.tests import tagged
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install')
class SpreadsheetDocuments(SpreadsheetTestCommon):

    def test_display_personal_thumbnail(self):
        user1 = self.env.user.create({'name': 'u1', 'login': 'u1'})
        user2 = user1.create({'name': 'u2', 'login': 'u2'})

        thumbnail1 = b'iVBORw0KGgoAAAANSUhEUgAAAJYAAACWCAYAAAA8AXHiAAAEy0lEQVR42u3bvY7kRBTF8XOvy+4xo4VgtQgkNM+ARIDIeQWelBcgIwQCCBASCQSrlZCG1fTHul2XwJ5eYAPQjO/0h/5H6tRnbFdX+Teutj+//iq61z9LjUsReurUcO2i1Xu+VcjSOra103WzSesImTZjp943UlqHtK1Xum52yrpTIdN27NQ3u0cdp6xe/6juj5+kMv/lTz6wpIiizvepHTVadT6kdYSkWouuEs9DkqLmXivN57F6ZEcJX0nF5xmrPvnAimgUcSX5XXJHL/mYOLBcoT73PGRTR5PcYY8/jyLFNKBCRxlYCpv763l3TN/1+ZMVm44fyR0LXCu3w/p3hHVQks3fQzouq6MM0cqiSNEcZcYao9Gb2qq1Nr2jS+yo8vTzCNm/OmzxCeHdjgcOrH008mikKEdQYWiMRvtotI+SpqkxPL2jytI74tCRO3iX6Ci9b9X5TvLdUVbDCFPjVb1tUjvcI7Vjeq7I7zAL9bY++Q5/+38dP8ozVpWrhtHxP2eTc+k4zmgiFx9USAcqRIWoEBWiQlSIClEhKjyTjoJflr0pWdtynuL4S6agwuU6WhtkHqkdJfZnca1Q4WKzievlm49kqmmDuMrV+qAX5ZWqfJ67TlSFQ/VJhfUYO/0uRIUm7Wqnb28/083q1xRcu4XWY69tvK8vn3+joRZ5wv1aVIWrexUe47nkElRokiL0cfebvnj2nYZYfvi6SetR+uHuc3W2myR/wios/1Th0y+FB03ZeXdM3/RW6+oawhZfDt2kdV2pznoPWcqSe1DhI68VKlx44rp329I3PeOYqPBMOooNuvKQ10hZCkffqrHx0HfyKvR7FQoVPjRDtHo1vNAvm080KmMpDN3te93uP9AYRWM0c8eJqnBU0T6aaVXkXeFDT0ONjbq5eqnb+mGK1mShvbW66X/XPpp5YGU9K/Ku8DRUOOfTZ9+rJP/mbxhbtTakQgQVnljHpva6Vu5v/naxmgZWYgcqPLH4NIRTb/q5yJAdpHTkqZB3hcsshewg/dvAYgfpUgOLHaSoMO25gh2kh2vBDtLz6eB3hQQho0I6UCEqRIWoEBWiQlSIClEhKiSoEBXSgQpRISpEhagQFaJCVIgKUSFBhaiQDlSIClEhKkSFqBAVokJUiAoJKkSFdKBCVIgKUSEqRIWoEBWiQlRIUCEqpAMVokJUiApRISpEhagQFaJCggpRIR2oEBWiQlSIClEhKkSFqBAVElSIdOhAhagQFaJCVIgKUSEqRIWokKBCpEMHKkSFqBAVokJUiApRISpEhQQVoik6UCEqRIWoEBWiQlSIClEhKiSoEE3RgQpRISpEhagQFaJCVIgKUSFBhWiKDlSIClEhKkSFqBAVokJUiAoJKkRTdKBCVIgKUSEqRIWoEBWiQlRIUCGaogMVokJUiApRISpEhagQFaJCggrRFB2oEBWiQlSIClEhKkSFqBAVElSIpuhAhagQFaJCVIgKUSEqRIWokKBCNIUKUSEqRIWoEBWiQlSIClEhKiSoEE2hQlSIClEhKkSFqBAVokJUiAoJKkRTqBAVokJUiApRISpEhagQFaJCggrRFCpEhagQFaJCVIgKUSEqRIWokJyaCrkEJCPlLS4t7aHzv6be+w8dl9PxF5hUd4vG3t6iAAAAAElFTkSuQmCC'
        thumbnail2 = b'iVBORw0KGgoAAAANSUhEUgAAAJYAAACWCAYAAAA8AXHiAAADq0lEQVR42u3Yu27jRgCF4TPkUJLtuAkSpNmn2DLv/wx5ggRYb2/rRnFSeLXYIF2AESPjO407/bpQHH8qn3//o3356+eMQ0truelaSupuzu75lNeXn1JKSzo8h2Fcst0e8/b2mJI+L7IMLdvtMfv9Q7dGSrLbHXLY7769f0np3PjPD/Pbp6/t5c9fs9pq8vjLa96+PHXNbLf7HI8PXRubzSGn004jSZ2mOaW0lNLSWrn9dbWZc30OKelyxxrHS6bNnNOp3y15GJZMmznnc79GKe1uGrW18n5Blfej6cZnYa797xd1h/fsX43cZ+PHzv+9Udvy/gDXv7fechm6XlT39GF8pEbdPp+yeT5lGJbbH4UtqY9zpu0pUz0nQzr9837JNJ0yTZu+R+F0yjxNfY+pO2nUabukPpwzjpcVjsKSsV6St2Ssc0rHC2sc59Q69/tAhqV/o7S7adTXl6e8fX3KWitp2W0POXQU21BaWhuy3z90fB3p3rj+RHMPjTrUJSlZTYXDuKTUJTmm692klKXvF+QWjdLuplHTfjh+Wm6/tlLX+t4wrnepNe5WNPWBVThN59R6zjCscxSO38Q2z/2kQ4UrqHCsl4z1knGNnxtuJDYqXEGFh/0ux8Mua20oLctu7CodKrx9Yyilfb9SV/m54aOIjQr/eWHxi1GhBhVSIRVSIRVSIRVSIRVSoRkValAhFVIhFVIhFVIhFVIhFZpRoQYVUiEVUiEVUiEVUiEVUqEZFWpQIRVSIRVSIRVSIRVSIRWaUaEGFVIhFVIhFVIhFVIhFVKhGRVqUCEVUiEVUiEVUiEVUiEVmlGhBhVSIRVSIRVSIRVSIRVSoRkValAhFVIhFVIhFVIhFVIhFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUqEGFZpRoQYVUiEVUiEVUiEVUiEVUqFRIRVqUCEVUiEVUiEVUiEVUiEVGhVSoQYVUiEVUiEVUiEVUiEVUqFRIRVqUCEVUiEVUiEVUiEVUiEVGhVSoQYVUiEVUiEVUiEVUiEVUqFRIRVqUCEVUiEVUiEVUiEVUiEVGhWSjgYVUiEVUiEVUiEVUiEVUqFRIeloUCEVUiEVUiEVUiEVUiEV2gdUobfAeqyufhSWlpTWtV9KS4nGLRt/A5jL3IqTyV0XAAAAAElFTkSuQmCC'
        spreadsheet = self.create_spreadsheet(name="My Spreadsheet")
        spreadsheet.with_user(user1).display_thumbnail = thumbnail1
        spreadsheet.with_user(user2).display_thumbnail = thumbnail2

        self.assertEqual(spreadsheet.with_user(user1).display_thumbnail, thumbnail1)
        self.assertEqual(spreadsheet.with_user(user2).display_thumbnail, thumbnail2)
        self.env.flush_all()
        self.env.invalidate_all()

        for user in [user1, user2]:
            attachements = self.env['ir.attachment'].with_user(user).search([
                ('res_id', '=', spreadsheet.id),
                ('res_model', '=', spreadsheet._name),
                ('res_field', '=', 'display_thumbnail')
            ])
            for att in attachements:
                # with self.assertRaises(AccessError):
                _ = att.datas
