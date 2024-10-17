# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from .models.event_event import EventEvent
from .models.event_quiz import EventQuiz, EventQuizAnswer, EventQuizQuestion
from .models.event_track import EventTrack
from .models.event_track_visitor import EventTrackVisitor
