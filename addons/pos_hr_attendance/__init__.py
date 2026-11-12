from . import models


def _pos_hr_attendance_post_init(env):
    env["res.company"].search([("attendance_kiosk_mode", "=", "barcode_manual")]).attendance_kiosk_mode = "manual"
