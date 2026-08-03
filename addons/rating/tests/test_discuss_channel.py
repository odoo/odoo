# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRatingDiscussChannel(TransactionCase):
    def test_channel_unlink_deletes_its_ratings(self):
        channel = self.env["discuss.channel"]._create_channel(name="Rated", group_id=None)
        other_channel = self.env["discuss.channel"]._create_channel(name="Other", group_id=None)
        channel_model = self.env["ir.model"]._get("discuss.channel")
        rating, other_rating = self.env["rating.rating"].create(
            [
                {"rating": 5, "res_id": channel.id, "res_model_id": channel_model.id},
                {"rating": 5, "res_id": other_channel.id, "res_model_id": channel_model.id},
            ],
        )
        channel.unlink()
        self.assertTrue(other_rating.exists())
        self.assertFalse(rating.exists())
