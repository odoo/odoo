# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Build Apple Wallet archives using an Odoo certificate signing callback."""
import hashlib
import json
import uuid
from datetime import datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageColor, ImageDraw, ImageOps

from odoo.tools.image import ImageProcess
from odoo.tools.translate import LazyTranslate


_lt = LazyTranslate(__name__)


def _pass_colors(event):
    """Use company branding and readable text colors."""
    def parse(value, fallback):
        try:
            return ImageColor.getrgb(value)[:3]
        except (ValueError, TypeError, AttributeError):
            return ImageColor.getrgb(fallback)

    def luminance(rgb):
        values = [channel / 255 for channel in rgb]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    background = parse(event.get("primary_color"), "#162A44")
    accent = parse(event.get("secondary_color"), "#77E1D3")
    level = luminance(background)
    foreground = (0, 0, 0) if level > 0.179 else (255, 255, 255)
    contrast = (max(level, luminance(accent)) + 0.05) / (min(level, luminance(accent)) + 0.05)
    label = accent if contrast >= 4.5 else foreground
    return background, foreground, label


def create_document(event, *, pass_type_identifier, team_identifier, organization_name, code_type="qr", translate=None):
    translate = translate or str
    event = dict(event)
    for name in ("venue", "city", "room", "instructions", "subtitle", "organizer", "address", "event_url", "timezone"):
        value = event.get(name) or ""
        if not isinstance(value, str):
            raise TypeError("Optional event text must be a string: %s" % name)
        event[name] = value
    formats = {"qr": "PKBarcodeFormatQR", "barcode": "PKBarcodeFormatCode128"}
    if code_type not in formats:
        raise ValueError("The code type must be qr or barcode.")
    required = ("event_name", "attendee", "ticket_type", "start", "end", "barcode")
    for field_name in required:
        if not isinstance(event.get(field_name), str) or not event[field_name].strip():
            raise ValueError(f"Missing event data: {field_name}")
    start, end = (
        datetime.fromisoformat(event[field_name].replace("Z", "+00:00"))
        for field_name in ("start", "end")
    )
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("Dates must include a time zone and the end must be after the start.")
    background, foreground, label_color = _pass_colors(event)

    def rgb(value):
        return "rgb(%s, %s, %s)" % value

    def field(key, label, value):
        return {"key": key, "label": translate(label), "value": value}
    document = {
        "formatVersion": 1, "passTypeIdentifier": pass_type_identifier,
        "serialNumber": event.get("registration_id") or str(uuid.uuid4()),
        "teamIdentifier": team_identifier, "organizationName": organization_name,
        "description": event["event_name"] + (" · " + event["subtitle"] if event["subtitle"] else ""),
        "logoText": organization_name,
        "backgroundColor": rgb(background), "foregroundColor": rgb(foreground),
        "labelColor": rgb(label_color),
        "preferredStyleSchemes": ["posterEventTicket", "eventTicket"],
        "relevantDate": event["start"],
        "relevantDates": [{"startDate": event["start"], "endDate": event["end"]}],
        "semantics": {
            "eventType": "PKEventTypeGeneric", "eventName": event["event_name"],
            "eventStartDate": event["start"], "eventEndDate": event["end"],
            "venueName": event["venue"], "venueRegionName": event["city"],
            "venueRoom": event["room"],
        },
        "barcodes": [{
            "format": formats[code_type],
            "message": event["barcode"],
            "messageEncoding": "utf-8",
            "altText": event["barcode"],
        }],
        "eventTicket": {
            "headerFields": [],
            "primaryFields": [],
            "secondaryFields": [field("event", _lt("Event"), event["event_name"]), field("venue", _lt("Venue"), event["venue"])],
            "auxiliaryFields": [field("start", _lt("Start"), event["start"]), field("end", _lt("End"), event["end"])],
            "backFields": [field("instructions", _lt("Instructions"), event["instructions"]), field("room", _lt("Room"), event["room"]), field("city", _lt("City"), event["city"]), field("timezone", _lt("Time zone"), event["timezone"]), field("registration", _lt("Registration"), event.get("registration_id", translate(_lt("Test"))))],
        },

    }
    document["eventTicket"]["backFields"][0:0] = [
        field("attendee", _lt("Attendee"), event["attendee"]),
        field("type", _lt("Ticket type"), event["ticket_type"]),
        field("subtitle", _lt("About this event"), event["subtitle"]),
        field("organizer", _lt("Organizer"), event["organizer"]),
        field("address", _lt("Address"), event["address"]),
        field("event_url", _lt("Event website"), event["event_url"]),
    ]
    document["semantics"] = {key: value for key, value in document["semantics"].items() if value}
    for field_group in document["eventTicket"].values():
        field_group[:] = [entry for entry in field_group if entry["value"]]
    for date_field in document["eventTicket"]["auxiliaryFields"]:
        date_field.update(dateStyle="PKDateStyleMedium", timeStyle="PKDateStyleShort")
    return document


def _build_pass(document, sign_manifest, background_image=None):
    background = ImageColor.getrgb(document["backgroundColor"])
    foreground = ImageColor.getrgb(document["foregroundColor"])
    files = {"pass.json": json.dumps(document, ensure_ascii=False).encode("utf-8")}
    for scale in (1, 2, 3):
        size = 29 * scale
        image = Image.new("RGB", (size, size), background)
        draw = ImageDraw.Draw(image)
        draw.line([(5 * scale, 7 * scale), (10 * scale, 22 * scale), (14 * scale, 12 * scale), (18 * scale, 22 * scale), (24 * scale, 7 * scale)], fill=foreground, width=2 * scale)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        files[f"icon{'@' + str(scale) + 'x' if scale > 1 else ''}.png"] = buffer.getvalue()
    source_image = None
    if background_image:
        # Process uploaded bytes through Odoo; no user-controlled filesystem path.
        if len(background_image) > 10 * 1024 * 1024:
            raise ValueError("The wallet background must not exceed 10 MB.")
        processed = ImageProcess(background_image, verify_resolution=True)
        if not processed.image:
            raise ValueError("Upload a supported raster image for the wallet background, such as PNG or JPEG.")
        if processed.image.width * processed.image.height > 2048 * 2048:
            raise ValueError("The wallet background must not exceed 2048 x 2048 pixels in total.")
        source_image = processed.image.convert("RGB")
    # Keep Wallet artwork separate from the printable event badge.
    for scale in (1, 2, 3):
        image = Image.new("RGB", (358 * scale, 448 * scale), background)
        if source_image is not None:
            image = ImageOps.fit(source_image, image.size, method=Image.Resampling.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        suffix = "@" + str(scale) + "x" if scale > 1 else ""
        files[f"artwork{suffix}.png"] = buffer.getvalue()
        legacy = image.resize((180 * scale, 220 * scale))
        buffer = BytesIO()
        legacy.save(buffer, format="PNG")
        files[f"background{suffix}.png"] = buffer.getvalue()
    # Apple requires SHA-1 file digests in manifest.json. These are not password
    # hashes or authorization tokens; the manifest is signed below using SHA-256.
    manifest = json.dumps({
        name: hashlib.sha1(data, usedforsecurity=False).hexdigest()
        for name, data in files.items()
    }).encode()
    signature = sign_manifest(manifest)
    files.update({"manifest.json": manifest, "signature": signature})
    output = BytesIO()
    # Write only an in-memory archive with filenames generated above. No archive
    # is read/extracted and no filesystem paths or member names come from users.
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def generate_event_pass(event, *, pass_type_identifier, team_identifier,
                        organization_name, sign_manifest, code_type="qr", translate=None):
    """Return raw .pkpass bytes using the caller's authorized signing callback.

    The model supplies validated identifiers and ``sign_manifest(manifest)``.
    That callback receives raw manifest bytes and returns a detached DER CMS
    signature containing the signing certificate and its WWDR intermediate.
    Certificate records and private keys are handled exclusively by the model.

    Pass env._ to translate labels and read event values in the same language.
    No filesystem access, HTTP requests or database writes are performed here.
    """
    if not all(isinstance(value, str) and value.strip() for value in
               (pass_type_identifier, team_identifier, organization_name)):
        raise ValueError("Signing identifiers and organization name are required.")
    document = create_document(
        event, pass_type_identifier=pass_type_identifier, team_identifier=team_identifier,
        organization_name=organization_name, code_type=code_type, translate=translate,
    )
    if code_type == "barcode":
        try:
            event["barcode"].encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("Code128 requires an ASCII registration code; use QR for Unicode.") from error
    return _build_pass(document, sign_manifest, background_image=event.get("background_image"))
