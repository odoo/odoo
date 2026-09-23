from psycopg import IntegrityError
from werkzeug.http import parse_options_header

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase
from odoo.tests.common import users
from odoo.tools import mute_logger

from odoo.addons.website_slides.tests import common


class TestResources(common.SlidesCase, HttpCase):
    @users("user_officer")
    @mute_logger("odoo")
    def test_constraints(self):
        link = self.env["slide.slide.resource"].create(
            {
                "name": "Test Link",
                "resource_type": "url",
                "link": "https://www.example.com",
                "slide_id": self.slide.id,
            }
        )
        self.assertFalse(link.data)

        resource = self.env["slide.slide.resource"].create(
            {
                "name": "Test Resource",
                "resource_type": "file",
                "data": "1111",
                "slide_id": self.slide.id,
            }
        )
        self.assertFalse(resource.link)

        self.assertEqual(len(self.slide.slide_resource_ids), 2)
        with self.assertRaises(
            ValidationError, msg="Cannot have a type link with a file"
        ):
            self.env["slide.slide.resource"].create(
                {
                    "name": "Raise Error Test Resource",
                    "resource_type": "url",
                    "link": "1111",
                    "data": "1111",
                    "slide_id": self.slide.id,
                }
            )
        self.assertEqual(len(self.slide.slide_resource_ids), 2)
        with self.assertRaises(
            IntegrityError, msg="Cannot have a type file with a link"
        ):
            self.env["slide.slide.resource"].create(
                {
                    "name": "Raise Error Test File With Link",
                    "resource_type": "file",
                    "link": "1111",
                    "slide_id": self.slide.id,
                }
            )
        with self.assertRaises(IntegrityError, msg="Cannot have an empty link"):
            self.env["slide.slide.resource"].create(
                {
                    "name": "Raise Error Test Empty URL",
                    "resource_type": "url",
                    "slide_id": self.slide.id,
                }
            )

    @users("user_officer")
    def test_download_file_name_extension(self):
        resource_name = 'Test Resource with special character éè!?&"'
        resource = self.env["slide.slide.resource"].create(
            {
                "name": resource_name,
                "file_name": "test.png",
                "resource_type": "file",
                "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAC4jAA"
                "AuIwF4pT92AAAAD0lEQVQIHQEEAPv/AIdaewLIAV0IjhGPAAAAAElFTkSuQmCC",
                "slide_id": self.slide.id,
            }
        )
        self.authenticate(self.env.user.login, self.env.user.login)

        for name, file_name, expected_download_name in (
            (resource_name, "test.xlsx", f"{resource_name}.xlsx"),
            (f"{resource_name}.xlsx", "test.xlsx", f"{resource_name}.xlsx"),
            (f"{resource_name}.txt", "test.xlsx", f"{resource_name}.txt.xlsx"),
            (f"{resource_name}.txt", "test.unknown_long_ext", f"{resource_name}.txt"),
            (resource_name, "test.unknown_long_ext", f"{resource_name}.png"),
            (resource_name, "test", f"{resource_name}.png"),
        ):
            resource.write({"name": name, "file_name": file_name})
            with self.subTest(
                name=name,
                file_name=file_name,
                expected_download_name=expected_download_name,
            ):
                content_disposition = self.url_open(resource.download_url).headers[
                    "Content-Disposition"
                ]
                _disposition, options = parse_options_header(content_disposition)
                self.assertEqual(options["filename"], expected_download_name)
