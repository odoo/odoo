"""Basic implementation to support SOAP-Attachments

See https://www.w3.org/TR/SOAP-attachments

"""

import base64

from cached_property import cached_property
from requests.structures import CaseInsensitiveDict


class MessagePack:
    def __init__(self, parts):
        self._parts = parts

    def __repr__(self):
        return "<MessagePack(attachments=[%s])>" % (
            ", ".join(repr(a) for a in self.attachments)
        )

    @property
    def root(self):
        return self._root

    def _set_root(self, root):
        self._root = root

    @cached_property
    def attachments(self):
        """Return a list of attachments.

        :rtype: list of Attachment

        """
        return [Attachment(part) for part in self._parts]

    def get_by_content_id(self, content_id):
        """get_by_content_id

        :param content_id: The content-id to return
        :type content_id: str
        :rtype: Attachment

        """
        for attachment in self.attachments:
            if attachment.content_id == content_id:
                return attachment


class Attachment:
    def __init__(self, part):
        encoding = part.encoding or "utf-8"
        self.headers = CaseInsensitiveDict(
            {k.decode(encoding): v.decode(encoding) for k, v in part.headers.items()}
        )
        self.content_type = self.headers.get("Content-Type", None)
        self.content_id = self.headers.get("Content-ID", None)
        self.content_location = self.headers.get("Content-Location", None)
        self._part = part

    def __repr__(self):
        return "<Attachment(%r, %r)>" % (self.content_id, self.content_type)

    @cached_property
    def content(self):
        """Return the content of the attachment

        :rtype: bytes or str

        """
        encoding = self.headers.get("Content-Transfer-Encoding", None)
        content = self._part.content

        if encoding == "base64":
            return base64.b64decode(content)
        elif encoding == "binary":
            return content.strip(b"\r\n")
        else:
            return content
