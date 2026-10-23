# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import speech_recognition as sr
from odoo import api,models, _


class VoiceRecognition(models.Model):
    """This class is used holds the voice recognition"""
    _name = 'voice.recognition'
    _description = 'Voice recognition'

    def get_the_browser(self):
        """Used to retrieve the browser/fastest method tht the user choose."""
        methode_browser = self.env['ir.config_parameter'].sudo().get_param(
            'voice_to_text.select_fastest_method')
        return methode_browser

    @api.model
    def recognize_speech(self):
        """This is used to recognizes the voice"""
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio_data = r.record(source, duration=15)
        try:
            text = r.recognize_google(audio_data, language='en-US')
            return text
        except sr.UnknownValueError:
            return 0

    @api.model
    def update_field(self, field, model, script, id):
        """This is used to write the voice text into the field"""
        if script:
            self.env[model].write({
                field: script
            })
        else:
            script = self.recognize_speech()
            if script:
                model = self.env[model].browse(id)
                model.sudo().write({
                    field: script
                })
            else:
                raise ValueError(_(
                    'Your Voice is not recognized Please try again'))
        return True
