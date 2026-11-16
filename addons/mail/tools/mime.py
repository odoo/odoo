import logging
from collections import namedtuple
from dataclasses import dataclass
from email.message import EmailMessage, MIMEPart

from markupsafe import Markup

from odoo.tools.mail import append_content_to_html, html_sanitize

_logger = logging.getLogger(__name__)

KNOWN_BAD_CONTENT_TYPES = ('binary/octet-stream', '*/*', 'bin/plain')

Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))


@dataclass(slots=True)
class _ClassifiedAttachment:
    attachment: Attachment
    # True for a file that belongs to an HTML body, such as an image shown
    # inside it. It is dropped when that body is not the one displayed.
    is_body_resource: bool = False


@dataclass(slots=True)
class _ExtractedPart:
    body: Markup
    attachments: list[_ClassifiedAttachment]


def extract_body_and_attachments(message: EmailMessage, is_bounce: bool = False) -> tuple[Markup, list[Attachment]]:
    """Return the HTML body and the attachments of a received message.

    The caller must sanitize the body: only its classes are stripped here.
    Malformed content headers of ``message`` are fixed in place.
    """
    extractor = _MimeExtractor(is_bounce=is_bounce, message_id=message.get('Message-ID'))
    result = extractor.extract(message, is_message_root=True)

    return result.body, [classified.attachment for classified in result.attachments]


class _MimeExtractor:
    def __init__(self, is_bounce: bool = False, message_id: str | None = None) -> None:
        self.is_bounce = is_bounce
        self.message_id = message_id

    def extract(self, part: MIMEPart, *, is_message_root: bool = False, is_related_root: bool = False) -> _ExtractedPart:
        """
        :param is_message_root: Whether this is the received message itself.
        :param is_related_root: Whether this is the body part selected by
            multipart/related. Ignore its attachment disposition and filename.
        """
        maintype, _sep, subtype = part.get_content_type().partition('/')

        # An embedded message is a document of its own. A typeless part of
        # a digest is one too (RFC 2046 section 5.1.5).
        if maintype == 'message':
            return self._extract_as_attachment(part)

        if maintype == 'multipart':
            if (
                not is_message_root
                and not is_related_root
                and part.get_content_disposition() == 'attachment'
            ):
                return self._extract_as_attachment(part)

            children = list(part.iter_parts())

            if subtype == 'alternative':
                return self._extract_alternative(children)
            if subtype == 'related':
                return self._extract_related(children, part)
            if subtype == 'encrypted':
                return self._extract_as_attachment(part)

            # an unknown subtype is handled as mixed (RFC 2046 section 5.1.3)
            return self._extract_mixed(children)

        return self._extract_leaf(part, is_message_root=is_message_root, is_related_root=is_related_root)

    def _extract_mixed(self, children: list[MIMEPart]) -> _ExtractedPart:
        body, attachments = Markup(), []

        for child in children:
            child_result = self.extract(child)

            if child_result.body:
                body = append_content_to_html(body, child_result.body, plaintext=False)
            attachments += child_result.attachments

            # The first body of a bounce is the failure reason. What follows
            # is diagnostics and the original message, which are read from
            # the raw message elsewhere.
            if self.is_bounce and body:
                break

        if body:
            # joining bodies can leave text outside of any element
            body = Markup(html_sanitize(body, sanitize_tags=False, strip_classes=True))

        return _ExtractedPart(body, attachments)

    def _extract_alternative(self, children: list[MIMEPart]) -> _ExtractedPart:
        """Use the last child that has a body: senders put the version they
        prefer last (RFC 2046 section 5.1.4).

        Body resources of the other children are dropped. Their other
        attachments are kept.
        """
        selected_result = None
        child_results = []

        for child in children:
            child_result = self.extract(child)
            child_results.append(child_result)

            if child_result.body.strip():
                selected_result = child_result

        selected_result = selected_result or _ExtractedPart(Markup(), [])

        attachments = [
            classified
            for child_result in child_results
            for classified in child_result.attachments
            if not classified.is_body_resource or child_result is selected_result
        ]

        return _ExtractedPart(selected_result.body, attachments)

    def _extract_related(self, children: list[MIMEPart], part: MIMEPart) -> _ExtractedPart:
        """Use the root child as body and keep the other children as files (RFC 2387)."""
        if not children:
            return _ExtractedPart(Markup(), [])

        root = self._resolve_related_root(children, part)
        root_result = self.extract(root, is_related_root=True)

        attachments = []
        for child in children:
            if child is root:
                attachments += root_result.attachments
            else:
                attachments.append(_ClassifiedAttachment(
                    self._attachment_from_part(child),
                    is_body_resource=child.get_content_disposition() != 'attachment',
                ))

        return _ExtractedPart(root_result.body, attachments)

    def _extract_leaf(self, part: MIMEPart, is_message_root: bool = False, is_related_root: bool = False) -> _ExtractedPart:
        self._normalize_content_type(part, is_message_root=is_message_root)

        if is_related_root:
            is_attachment = False
        elif is_message_root:
            # a filename alone must not hide the only content of the message
            is_attachment = part.get_content_disposition() == 'attachment'
        else:
            is_attachment = self._is_attachment(part)

        content_type = part.get_content_type()

        if not is_attachment and content_type == 'text/plain':
            text = self._decode_text(part)
            body = (
                Markup('\n<pre>%s</pre>\n') % text
                if text.strip()
                else Markup()
            )
            return _ExtractedPart(body, [])

        if not is_attachment and content_type == 'text/html':
            body = html_sanitize(self._decode_text(part), sanitize_tags=False, strip_classes=True)
            return _ExtractedPart(Markup(body), [])

        return self._extract_as_attachment(part)

    def _extract_as_attachment(self, part: MIMEPart) -> _ExtractedPart:
        return _ExtractedPart(
            Markup(),
            [_ClassifiedAttachment(self._attachment_from_part(part))],
        )

    def _resolve_related_root(self, children: list[MIMEPart], part: MIMEPart) -> MIMEPart:
        start = (part.get_param('start') or '').strip().strip('<>')

        if start:
            for child in children:
                content_id = (child.get('content-id') or '').strip().strip('<>')
                if content_id == start:
                    return child

            _logger.warning(
                "Message %r containing a multipart/related start %r that matches "
                "no part, using the first part",
                self.message_id, start,
            )

        return children[0]

    def _is_attachment(self, part: MIMEPart) -> bool:
        return part.get_content_disposition() == 'attachment' or bool(part.get_filename())

    def _normalize_content_type(self, part: MIMEPart, is_message_root: bool = False) -> None:
        """The email package reads a part with a missing or malformed content
        type as text/plain. Decoding it as text would corrupt binary content.
        """
        content_type = part.get('Content-Type')

        if content_type is None:
            is_digest_message = part.get_content_maintype() == 'message'
            # a message without MIME headers is plain text (RFC 2045 section 5.2)
            is_plain_message = is_message_root and part.get_content_disposition() != 'attachment'
            if is_digest_message or is_plain_message:
                return

            _logger.warning(
                "Message %r has no Content-Type, assuming 'application/octet-stream'",
                self.message_id,
            )
            part.add_header('Content-Type', 'application/octet-stream')
            return

        mimetype, _sep, params = content_type.partition(';')
        mimetype = mimetype.strip().lower()
        maintype, _sep, subtype = mimetype.partition('/')

        if maintype and subtype and mimetype not in KNOWN_BAD_CONTENT_TYPES:
            return

        _logger.warning(
            "Message %r containing an unexpected Content-Type %r, "
            "assuming 'application/octet-stream'",
            self.message_id, mimetype,
        )
        part.replace_header(
            'Content-Type',
            f'application/octet-stream; {params.strip()}' if params else 'application/octet-stream',
        )

    def _decode_text(self, part: MIMEPart) -> str:
        if not part.get_param('charset'):
            # the email package would assume ASCII
            part.set_charset('utf-8')

        return part.get_content()

    def _attachment_from_part(self, part: MIMEPart) -> Attachment:
        self._normalize_content_type(part)

        maintype = part.get_content_maintype()
        if maintype == 'message':
            # an EmailMessage for message/rfc822, serialized when stored
            content = part.get_content()
        elif maintype == 'multipart':
            content = part.as_bytes()
        elif maintype == 'text':
            content = self._decode_text(part)
        else:
            # get_content() raises KeyError for a main type the email package
            # does not know, such as font/woff
            content = part.get_payload(decode=True)

        info = {'encoding': part.get_content_charset()}
        if content_id := part.get('content-id'):
            info['cid'] = content_id.strip().strip('<>')

        return Attachment(part.get_filename() or 'attachment', content, info)
