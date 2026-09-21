import logging
from pathlib import Path

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config

from ..tools import embedder

_logger = logging.getLogger(__name__)

DEFAULT_MODEL_FILE = "wespeaker_en_voxceleb_CAM++.onnx"
MIN_ENROLL_SECONDS = 10.0
MAX_VOICE_SECONDS = 60.0
MAX_ENROLL_BYTES = 10 * 1024 * 1024
DEFAULT_THRESHOLD = 0.65
DEFAULT_MARGIN = 0.08

_EMBEDDERS = {}
_WARNED = set()


class SpeechVoiceprint(models.Model):
    _name = "speech.voiceprint"
    _description = "Voiceprint"
    _rec_name = "employee_id"
    _order = "employee_id"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(related="employee_id.user_id")
    company_id = fields.Many2one(related="employee_id.company_id")
    embedding = fields.Json(
        groups="base.group_system",
        help="L2-normalised speaker embedding; never the audio",
    )
    dim = fields.Integer(readonly=True)
    sample_seconds = fields.Float(
        digits=(6, 1),
        readonly=True,
    )
    model_name = fields.Char(readonly=True)
    consent_at = fields.Datetime(required=True)
    enrolled_at = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)

    _employee_unique = models.Constraint(
        "UNIQUE(employee_id)", "This employee already has a voiceprint."
    )

    @api.model
    def _model_path(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "speech_voiceprint.model_path",
                str(Path(config["data_dir"]) / "models" / DEFAULT_MODEL_FILE),
            )
        )

    @api.model
    def _embedder(self):
        path = self._model_path()
        if path in _EMBEDDERS:
            return _EMBEDDERS[path]
        if not Path(path).is_file():
            _warn_once(path, "Speaker model missing at %s; voices stay anonymous", path)
            return None
        try:
            _EMBEDDERS[path] = embedder.SpeakerEmbedder(path)
        except (ImportError, ValueError) as error:
            _warn_once(
                path,
                "Speaker model at %s unusable (%s); voices stay anonymous",
                path,
                error,
            )
            return None
        return _EMBEDDERS[path]

    @api.model
    def _enrolment_phrase(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "speech_voiceprint.phrase"
        ) or self.env._(
            "Good morning. I record this so that the system can recognise my voice "
            "in our calls and meetings. Six thick thistle sticks, a quick brown fox "
            "and a lazy dog: every sound of the language, spoken at my usual pace, "
            "for about half a minute, until the recording is long enough to count."
        )

    @api.model
    def _thresholds(self):
        params = self.env["ir.config_parameter"].sudo()
        return (
            _float_param(params, "speech_voiceprint.threshold", DEFAULT_THRESHOLD),
            _float_param(params, "speech_voiceprint.margin", DEFAULT_MARGIN),
        )

    @api.model
    def _decode(self, audio_bytes):
        try:
            return embedder.decode_audio(audio_bytes)
        except ImportError as error:
            raise UserError(
                self.env._("Voice recognition is not installed on this server yet.")
            ) from error
        except Exception as error:
            raise UserError(
                self.env._("The recording could not be read as audio: %s", error)
            ) from error

    @api.model
    def _embed_samples(self, samples, spans=None):
        model = self._embedder()
        if model is None:
            return None, 0.0
        if spans is not None:
            samples = embedder.slice_spans(
                samples, spans, max_seconds=MAX_VOICE_SECONDS
            )
        seconds = samples.size / embedder.SAMPLE_RATE
        return model.embed(samples), seconds

    @api.model
    def _embed_audio(self, audio_bytes, spans=None):
        if self._embedder() is None:
            return None, 0.0
        return self._embed_samples(self._decode(audio_bytes), spans)

    @api.model
    def _voice_embedding(self, samples, spans):
        vector, _seconds = self._embed_samples(samples, spans)
        return vector

    @api.model
    def _enroll(self, employee, audio_bytes):
        if len(audio_bytes) > MAX_ENROLL_BYTES:
            raise UserError(self.env._("The recording is too large."))
        if self._embedder() is None:
            raise UserError(
                self.env._("Voice recognition is not installed on this server yet.")
            )
        existing = (
            self.sudo()
            .with_context(active_test=False)
            .search([("employee_id", "=", employee.id)], limit=1)
        )
        if existing and not existing.active:
            raise UserError(
                self.env._(
                    "Your voiceprint was deactivated; ask for it to be reactivated "
                    "before recording again."
                )
            )
        vector, seconds = self._embed_audio(audio_bytes)
        if seconds < MIN_ENROLL_SECONDS:
            raise UserError(
                self.env._(
                    "The recording is too short (%(got).0f s). Read the whole phrase; "
                    "at least %(need).0f seconds are needed.",
                    got=seconds,
                    need=MIN_ENROLL_SECONDS,
                )
            )
        if vector is None:
            raise UserError(
                self.env._("No voice could be extracted from the recording.")
            )
        now = fields.Datetime.now()
        vals = {
            "embedding": vector,
            "dim": len(vector),
            "sample_seconds": round(seconds, 1),
            "model_name": Path(self._model_path()).name,
            "consent_at": now,
            "enrolled_at": now,
        }
        if existing:
            existing.write(vals)
            return existing
        return self.sudo().create({"employee_id": employee.id, **vals})

    @api.model
    def _candidates(self, company):
        prints = self.sudo().search([("company_id", "in", (company.id, False))])
        current = Path(self._model_path()).name
        usable = prints.filtered(lambda p: p.model_name == current)
        if len(usable) < len(prints):
            _logger.info(
                "%s voiceprint(s) made with another model skipped",
                len(prints) - len(usable),
            )
        return usable

    @api.model
    def _match(self, vector, prints):
        if vector is None or not prints:
            return None, 0.0
        threshold, margin = self._thresholds()
        ranked = sorted(
            ((embedder.cosine(vector, vp.embedding), vp) for vp in prints),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score < threshold or best_score - runner_up < margin:
            return None, best_score
        return best, best_score

    @api.model
    def _identify_speakers(self, attachment):
        voices = attachment.speaker_ids.filtered(
            lambda s: not s.partner_id and not s.employee_id
        )
        if not voices or self._embedder() is None:
            return 0
        prints = list(self._candidates(attachment.company_id or self.env.company))
        if not prints:
            return 0
        samples = self._decode(attachment.sudo()._get_content())
        assigned = 0
        for voice in voices:
            spans = [
                (cue["start"], cue["end"])
                for cue in attachment.transcript_cues or []
                if cue.get("speaker") == voice.label
                and (cue.get("end") or 0.0) > (cue.get("start") or 0.0)
            ]
            best, score = self._match(self._voice_embedding(samples, spans), prints)
            if best is None:
                continue
            voice._assign_employee(best.employee_id, score)
            prints.remove(best)
            assigned += 1
        return assigned


def _warn_once(path, message, *args):
    if path not in _WARNED:
        _WARNED.add(path)
        _logger.warning(message, *args)


def _float_param(params, key, default):
    try:
        return float(params.get_param(key, default))
    except TypeError, ValueError:
        _logger.warning("%s is not a number; using %s", key, default)
        return default
