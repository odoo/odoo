import base64
import datetime
import logging
from urllib.parse import quote as url_quote

import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# Default booking duration offered by the portal form (in minutes).
DEFAULT_BOOKING_MINUTES = 60

# A room can be reserved this many months ahead. The room schedule popup looks
# the same distance back, so both edges of the window line up.
BOOKING_WINDOW_MONTHS = 6

# Human readable booking states, used by the portal popup.
BOOKING_STATE_LABELS = {
    "booked": "จองแล้ว",
    "in_use": "กำลังใช้",
    "done": "เสร็จสิ้น",
    "cancelled": "ยกเลิก",
}

# Extensions accepted for uploaded documents (checked on the filename suffix).
ALLOWED_DOC_EXT = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".zip", ".rar", ".txt",
)

# Hard limits to protect the server from oversized uploads.
MAX_RESUME_SIZE = 10 * 1024 * 1024      # 10 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024    # 10 MB per supporting document
MAX_DOCUMENTS = 5


class AutoInfoWebsite(http.Controller):
    """Controllers for the Auto-Info corporate website and employee portal."""

    # ------------------------------------------------------------------
    # Employee portal
    # ------------------------------------------------------------------
    @http.route(
        ["/employee-portal"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def employee_portal(self, booked=None, booking_error=None, **kwargs):
        """Employee portal homepage.

        Only authenticated internal users can access this page.
        """
        Announcement = request.env["announcement"]
        today = datetime.date.today()
        announcements = Announcement.sudo().search(
            [
                ("published", "=", True),
                "|",
                ("expiry_date", "=", False),
                ("expiry_date", ">=", today),
            ],
            limit=5,
            order="published_date desc, create_date desc",
        )
        return request.render(
            "od19_website.od19_employee_portal",
            {
                "user": request.env.user,
                "datetime": datetime,
                "announcements": announcements,
                "rooms": self._od19_room_overview(),
                "today": today,
                "now": fields.Datetime.now(),
                "default_minutes": DEFAULT_BOOKING_MINUTES,
                "booked": booked,
                "booking_error": booking_error,
                "my_bookings": self._od19_my_upcoming_bookings(),
                "min_booking_date": today,
                "max_booking_date": today
                + relativedelta(months=BOOKING_WINDOW_MONTHS),
                "booking_window_months": BOOKING_WINDOW_MONTHS,
                "approval_summary": self._od19_approval_data()["summary"],
            },
        )

    # ------------------------------------------------------------------
    # Approval Center (view-only)
    # ------------------------------------------------------------------
    @http.route(
        ["/my/approvals"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def od19_my_approvals(self, **kwargs):
        """Approval Center page: what I must approve + my own requests."""
        return request.render(
            "od19_website.od19_approval_center", self._od19_approval_data()
        )

    def _od19_approval_data(self):
        """Aggregate every active source into 2 tabs x 4 groups."""
        Source = request.env["od19.approval.source"].sudo()
        approver = {"pending": [], "incoming": [], "done": [], "rejected": []}
        requester = {"pending": [], "incoming": [], "done": [], "rejected": []}
        for source in Source.search([("active", "=", True)]):
            for key, records in source._od19_classify_for_approver().items():
                approver[key].extend(source._od19_build_rows(records))
            for key, records in source._od19_classify_for_requester().items():
                requester[key].extend(source._od19_build_rows(records))
        return {
            "user": request.env.user,
            "datetime": datetime,
            "approver": approver,
            "requester": requester,
            "summary": Source._od19_summary(approver["pending"]),
        }

    @http.route(
        ["/employee-portal/book-room"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        sitemap=False,
    )
    def portal_book_room(self, **post):
        """Create a meeting-room booking straight from the portal form.

        The booking is confirmed immediately; there is no approval step.
        Any rule violation is reported back to the same page.
        """
        redirect_url = "/employee-portal"
        try:
            room_id = int(post.get("room_id") or 0)
        except (TypeError, ValueError):
            room_id = 0

        values = {
            "room_id": room_id,
            "name": (post.get("name") or "").strip(),
            "booking_date": (post.get("booking_date") or "").strip(),
            "start_time": (post.get("start_time") or "").strip(),
            "end_time": (post.get("end_time") or "").strip(),
        }

        def _fail(message):
            return request.redirect(
                "%s?booking_error=%s" % (redirect_url, url_quote(message))
            )

        if not values["room_id"] or not request.env["od19.meeting.room"].sudo().browse(
            values["room_id"]
        ).exists():
            return _fail("กรุณาเลือกห้องประชุม")
        if not values["name"]:
            return _fail("กรุณากรอกหัวข้อการประชุม")
        if not values["booking_date"] or not values["start_time"] or not values["end_time"]:
            return _fail("กรุณาระบุวันที่และเวลาให้ครบถ้วน")

        try:
            start_dt = self._od19_to_utc(values["booking_date"], values["start_time"])
            end_dt = self._od19_to_utc(values["booking_date"], values["end_time"])
        except ValueError:
            return _fail("รูปแบบวันที่หรือเวลาไม่ถูกต้อง")

        try:
            participant_count = int(post.get("participant_count") or 2)
        except (TypeError, ValueError):
            participant_count = 2

        try:
            booking = (
                request.env["od19.meeting.room.booking"]
                .sudo()
                .create(
                    {
                        "name": values["name"],
                        "room_id": values["room_id"],
                        "organizer_id": request.env.user.id,
                        "participant_count": max(participant_count, 1),
                        "start_datetime": start_dt,
                        "end_datetime": end_dt,
                        "purpose": (post.get("purpose") or "").strip(),
                    }
                )
            )
        except (ValidationError, UserError) as exc:
            message = getattr(exc, "args", [None])[0] or "ไม่สามารถจองห้องประชุมได้"
            return _fail(str(message))

        return request.redirect(
            "%s?booked=%s" % (redirect_url, url_quote(booking.reference or ""))
        )

    @http.route(
        ["/employee-portal/room-schedule"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
        sitemap=False,
    )
    def portal_room_schedule(self, room_id=None, **kwargs):
        """Return when a room is already taken, as JSON.

        The portal fetches this when a room tile is clicked, so the tiles stay
        light and only the schedule the user actually looks at is loaded.
        """
        try:
            room_id = int(room_id or 0)
        except (TypeError, ValueError):
            room_id = 0

        schedule = self._od19_room_schedule(room_id)
        if schedule is None:
            return request.make_json_response({"error": "not_found"}, status=404)
        return request.make_json_response(schedule)

    # ------------------------------------------------------------------
    # Careers
    # ------------------------------------------------------------------
    def _od19_get_openings(self):
        """Return all published and still-open job openings."""
        openings = request.env["od19.job.opening"].sudo().search(
            [("is_published", "=", True)], order="sequence, id desc"
        )
        return openings.filtered(lambda opening: opening.is_open)

    @http.route(
        ["/careers", "/careers/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def careers(self, department=None, page=1, **kwargs):
        """Public listing of open job positions."""
        openings = self._od19_get_openings()

        departments = [
            ("industrial", "Industrial Automation", "fa-industry"),
            ("building", "Building Automation", "fa-building"),
            ("terminal", "Terminal Automation", "fa-tint"),
            ("support", "Sales & Administration", "fa-briefcase"),
        ]
        # Only advertise departments that actually have an opening.
        active_departments = {
            opening.department for opening in openings
        }
        department_cards = [
            {
                "key": key,
                "label": label,
                "icon": icon,
                "count": len(openings.filtered(lambda o, k=key: o.department == k)),
            }
            for key, label, icon in departments
            if key in active_departments
        ]

        if department:
            openings = openings.filtered(lambda o: o.department == department)

        return request.render(
            "od19_website.od19_careers_list",
            {
                "openings": openings,
                "department_cards": department_cards,
                "current_department": department,
                "total_count": len(self._od19_get_openings()),
            },
        )

    @http.route(
        ["/careers/<int:job_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def career_detail(self, job_id, **kwargs):
        """Detail page of a single job opening."""
        opening = request.env["od19.job.opening"].sudo().browse(job_id)
        if not opening.exists() or not opening.is_open:
            raise request.not_found()

        related = request.env["od19.job.opening"].sudo().search(
            [
                ("is_published", "=", True),
                ("id", "!=", opening.id),
                ("department", "=", opening.department),
            ],
            order="sequence, id desc",
            limit=3,
        )
        related = related.filtered(lambda o: o.is_open)
        return request.render(
            "od19_website.od19_careers_detail",
            {"opening": opening, "related": related},
        )

    @http.route(
        ["/careers/<int:job_id>/apply"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
        sitemap=False,
    )
    def career_apply(self, job_id, **post):
        """Application form (GET) and submission handler (POST)."""
        opening = request.env["od19.job.opening"].sudo().browse(job_id)
        if not opening.exists() or not opening.is_open:
            raise request.not_found()

        errors = {}
        values = {"job_id": opening.id}

        if request.httprequest.method == "POST":
            file_storage = request.httprequest.files

            name = (post.get("name") or "").strip()
            email = (post.get("email") or "").strip()
            phone = (post.get("phone") or "").strip()
            consent = post.get("consent")

            if not name:
                errors["name"] = "Please enter your full name."
            if not email or "@" not in email or "." not in email.split("@")[-1]:
                errors["email"] = "Please enter a valid email address."
            if not phone:
                errors["phone"] = "Please enter a contact phone number."
            if not consent:
                errors["consent"] = "Please accept the privacy notice before submitting."

            resume_file = file_storage.get("resume")
            documents = [
                doc for doc in file_storage.getlist("documents") if doc and doc.filename
            ]

            if not resume_file or not resume_file.filename:
                errors["resume"] = "Please attach your resume / CV."
            elif not resume_file.filename.lower().endswith(ALLOWED_DOC_EXT):
                errors["resume"] = "Unsupported resume file type."
            else:
                resume_file.seek(0, 2)
                if resume_file.tell() > MAX_RESUME_SIZE:
                    errors["resume"] = "The resume must not exceed 10 MB."
                resume_file.seek(0)

            if len(documents) > MAX_DOCUMENTS:
                errors["documents"] = "You can attach up to %s documents." % MAX_DOCUMENTS
            for document in documents:
                document.seek(0, 2)
                if document.tell() > MAX_DOCUMENT_SIZE:
                    errors["documents"] = (
                        "Each supporting document must not exceed 10 MB."
                    )
                    break
                document.seek(0)

            if not errors:
                try:
                    application = request.env["od19.job.application"].sudo().create(
                        {
                            "job_id": opening.id,
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "current_company": (post.get("current_company") or "").strip(),
                            "current_position": (post.get("current_position") or "").strip(),
                            "years_experience": self._od19_to_float(
                                post.get("years_experience")
                            ),
                            "expected_salary": (post.get("expected_salary") or "").strip(),
                            "available_date": post.get("available_date") or False,
                            "source": (post.get("source") or "").strip(),
                            "cover_letter": (post.get("cover_letter") or "").strip(),
                        }
                    )
                    self._od19_attach_files(application, resume_file, documents)
                except Exception:  # noqa: BLE001 - never expose a traceback to applicants
                    _logger.exception("Failed to record job application.")
                    return request.redirect("/careers/%s/apply?error=1" % opening.id)

                return request.redirect(
                    "/careers/thank-you?ref=%s" % (application.reference or "")
                )

            # Keep what the applicant typed so the form can be re-displayed.
            values.update(post)

        return request.render(
            "od19_website.od19_careers_apply",
            {
                "opening": opening,
                "errors": errors,
                "values": values,
                "allowed_ext": ", ".join(ALLOWED_DOC_EXT),
                "max_documents": MAX_DOCUMENTS,
            },
        )

    @http.route(
        ["/careers/thank-you"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def career_thank_you(self, ref=None, **kwargs):
        """Confirmation page shown after a successful submission."""
        return request.render(
            "od19_website.od19_careers_thank_you",
            {"reference": ref, "job": kwargs.get("job")},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _od19_room_overview():
        """Return every active room with its live status and next slot.

        Times are converted to the user's timezone so the portal shows local
        hours and the room status is meaningful for everyone at a glance.
        """
        rooms = (
            request.env["od19.meeting.room"]
            .sudo()
            .search([("active", "=", True)], order="sequence, name, id")
        )
        overview = []
        for room in rooms:
            current = room._od19_current_booking()
            next_booking = room._od19_next_booking()
            if current:
                status, status_label = "busy", "กำลังใช้งาน"
            elif next_booking:
                status, status_label = "reserved", "ถูกจองแล้ว"
            else:
                status, status_label = "free", "ว่าง"
            overview.append(
                {
                    "room": room,
                    "current": current,
                    "next": next_booking,
                    "status": status,
                    "status_label": status_label,
                    "busy_until": (
                        AutoInfoWebsite._od19_local(current.end_datetime, "%H:%M")
                        if current
                        else None
                    ),
                    "next_label": (
                        AutoInfoWebsite._od19_local(
                            next_booking.start_datetime, "%d/%m %H:%M"
                        )
                        if next_booking
                        else None
                    ),
                }
            )
        return overview

    @staticmethod
    def _od19_room_schedule(room_id, months=BOOKING_WINDOW_MONTHS, limit=200):
        """Return when a room is taken, from ``months`` back to ``months`` ahead.

        Cancelled bookings are left out because they never held the room, and
        times are converted to the user's timezone so the popup shows the same
        local hours as the rest of the portal. ``None`` means the room is gone.
        """
        room = request.env["od19.meeting.room"].sudo().browse(room_id)
        if not room.exists():
            return None

        now = fields.Datetime.now()
        bookings = (
            request.env["od19.meeting.room.booking"]
            .sudo()
            .search(
                [
                    ("room_id", "=", room.id),
                    ("state", "!=", "cancelled"),
                    ("start_datetime", ">=", now - relativedelta(months=months)),
                    ("start_datetime", "<=", now + relativedelta(months=months)),
                ],
                order="start_datetime desc",
                limit=limit,
            )
        )

        history = []
        upcoming = []
        for booking in bookings:
            entry = {
                "reference": booking.reference or "",
                "name": booking.name or "",
                "organizer": booking.organizer_id.name or "",
                "date": AutoInfoWebsite._od19_local(
                    booking.start_datetime, "%d/%m/%Y"
                ),
                "start": AutoInfoWebsite._od19_local(booking.start_datetime, "%H:%M"),
                "end": AutoInfoWebsite._od19_local(booking.end_datetime, "%H:%M"),
                "state_label": BOOKING_STATE_LABELS.get(booking.state, booking.state),
            }
            if booking.end_datetime and booking.end_datetime > now:
                upcoming.append(entry)
            else:
                history.append(entry)
        upcoming.reverse()  # soonest booking first

        return {
            "room": {
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "floor": room.floor or "",
            },
            "window_months": months,
            "busy_now": bool(room._od19_current_booking()),
            "history": history,
            "upcoming": upcoming,
        }

    @staticmethod
    def _od19_local(dt, fmt="%d/%m/%Y %H:%M"):
        """Format a UTC datetime in the current user's timezone."""
        if not dt:
            return ""
        tz_name = request.env.user.tz or "UTC"
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        return pytz.UTC.localize(dt).astimezone(tz).strftime(fmt)

    @staticmethod
    def _od19_my_upcoming_bookings():
        """Return the current user's upcoming bookings, soonest first."""
        bookings = (
            request.env["od19.meeting.room.booking"]
            .sudo()
            .search(
                [
                    ("organizer_id", "=", request.env.user.id),
                    ("state", "in", ("booked", "in_use")),
                    ("end_datetime", ">=", fields.Datetime.now()),
                ],
                order="start_datetime asc",
                limit=5,
            )
        )
        return [
            {
                "name": booking.name,
                "room": booking.room_id.name,
                "start": AutoInfoWebsite._od19_local(
                    booking.start_datetime, "%d/%m %H:%M"
                ),
                "end": AutoInfoWebsite._od19_local(booking.end_datetime, "%H:%M"),
                "state_label": BOOKING_STATE_LABELS.get(booking.state, booking.state),
            }
            for booking in bookings
        ]

    @staticmethod
    def _od19_to_utc(date_str, time_str):
        """Combine a date and a time entered in the user's timezone into UTC.

        Odoo stores datetimes in UTC, so the browser input (which is local) has
        to be converted. Falls back to UTC when the user has no timezone set.
        """
        naive = datetime.datetime.strptime(
            "%s %s" % (date_str, time_str[:5]), "%Y-%m-%d %H:%M"
        )
        tz_name = request.env.user.tz or "UTC"
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        return tz.localize(naive).astimezone(pytz.UTC).replace(tzinfo=None)

    @staticmethod
    def _od19_to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _od19_attach_files(application, resume_file, documents):
        """Store the resume and the supporting documents as attachments."""
        if resume_file and resume_file.filename:
            resume_file.seek(0)
            application.write(
                {
                    "resume": base64.b64encode(resume_file.read()),
                    "resume_filename": resume_file.filename,
                }
            )

        attachment_ids = []
        for document in documents:
            document.seek(0)
            attachment = (
                request.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": document.filename,
                        "datas": base64.b64encode(document.read()),
                        "res_model": "od19.job.application",
                        "res_id": application.id,
                    }
                )
            )
            attachment_ids.append(attachment.id)

        if attachment_ids:
            application.write({"document_ids": [(6, 0, attachment_ids)]})
