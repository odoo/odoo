# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from ..fields import FSImage


class TestImageModel(models.Model):
    _name = "test.image.model"
    _description = "Test Model"
    _log_access = False

    fs_image = FSImage(verify_resolution=False)
    fs_image_1024 = FSImage("Image 1024", max_width=1024, max_height=1024)


class TestRelatedImageModel(models.Model):
    _name = "test.related.image.model"
    _description = "Test Related Image Model"
    _log_access = False

    fs_image = FSImage(verify_resolution=False)
    # resized fields stored (as attachment) for performance
    fs_image_1024 = FSImage(
        "Image 1024", related="fs_image", max_width=1024, max_height=1024, store=True
    )
    fs_image_512 = FSImage(
        "Image 512", related="fs_image", max_width=512, max_height=512, store=True
    )
