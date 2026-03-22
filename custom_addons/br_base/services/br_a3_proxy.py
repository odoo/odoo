import socket


class BrA3Proxy:
    SOCKET_PATH = "/tmp/br_a3.sock"

    def sign_xml(self, xml_bytes: bytes, reference_uri: str) -> bytes:
        payload = reference_uri.encode() + b"\n" + xml_bytes
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(self.SOCKET_PATH)
            client.sendall(payload)
            chunks = []
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks)

