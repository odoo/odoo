# ./odoo-bin --config=../.vscode/odoo.conf -u smartclass --test-enable --test-tags=:TestVolume

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestVolume(odoo.tests.HttpCase):

    def test_volume_model(self):
        volume0 = self.env["smartclass.volume"].create({
            "name": "volume 0",
            "width": 2.56,
            "height": 1.34,
        })
        self.assertEqual(volume0.volume, 0)
        self.assertEqual(volume0.category, "small")
        volume1 = self.env["smartclass.volume"].create({
            "name": "volume 1",
            "depth": 1,
            "width": 1,
            "height": 0.2,
        })
        self.assertEqual(volume1.volume, 0.2)
        self.assertEqual(volume1.category, "small")
        volume2 = self.env["smartclass.volume"].create({
            "name": "volume 2",
            "depth": 7.24,
            "width": 2.56,
            "height": 1.34,
        })
        self.assertAlmostEqual(volume2.volume, 24.84, places=2)
        self.assertEqual(volume2.category, "medium")

    def test_tour_create_volumes(self):
        # Be sure to be in light mode
        self.start_tour('/odoo', 'tour_create_volumes', login="admin")
        volumes = self.env["smartclass.volume"].search([])
        self.assertEqual(len(volumes), 5, "There should be 5 volumes.")
        self.assertEqual(volumes[0].volume, 40.93)
        self.assertEqual(volumes[1].volume, 2)
        self.assertEqual(volumes[2].volume, 6)
        self.assertEqual(volumes[3].volume, 60)
        self.assertEqual(volumes[4].volume, 504000)

