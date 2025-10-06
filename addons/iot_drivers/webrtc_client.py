import asyncio
import json
import logging
from threading import Thread
from aiortc import RTCDataChannel, RTCPeerConnection, RTCSessionDescription

from odoo.addons.iot_drivers.tools import communication

_logger = logging.getLogger(__name__)


class WebRtcClient(Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.connections: set[RTCDataChannel] = set()
        self.chunked_message_in_progress: dict[RTCDataChannel, str] = {}
        self.event_loop = asyncio.new_event_loop()

    def offer(self, request: dict):
        return asyncio.run_coroutine_threadsafe(
            self._offer(request), self.event_loop
        ).result()

    def send(self, data: dict):
        asyncio.run_coroutine_threadsafe(
            self._send(data), self.event_loop
        )

    async def _offer(self, request: dict):
        offer = RTCSessionDescription(sdp=request["sdp"], type=request["type"])

        peer_connection = RTCPeerConnection()

        @peer_connection.on("datachannel")
        def on_datachannel(channel: RTCDataChannel):
            self.connections.add(channel)

            @channel.on("message")
            async def on_message(message_str: str):
                # Handle chunked message
                if self.chunked_message_in_progress.get(channel) is not None:
                    if message_str == "chunked_end":
                        message_str = self.chunked_message_in_progress.pop(channel)
                    else:
                        self.chunked_message_in_progress[channel] += message_str
                        return
                elif message_str == "chunked_start":
                    self.chunked_message_in_progress[channel] = ""
                    return

                # Handle regular message
                message = json.loads(message_str)
                message["data"]["session_id"] = message["session_id"]
                result = await self.event_loop.run_in_executor(
                    None,
                    lambda: communication.handle_message(
                        message["message_type"], device_identifier=message["device_identifier"], **message["data"]
                    )
                )
                if result:
                    self.send(result)

            @channel.on("close")
            def on_close():
                self.connections.discard(channel)

        @peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            if peer_connection.connectionState == "failed":
                await peer_connection.close()

        await peer_connection.setRemoteDescription(offer)

        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)

        return {"sdp": peer_connection.localDescription.sdp, "type": peer_connection.localDescription.type}

    async def _send(self, data: dict):
        for connection in self.connections:
            connection.send(json.dumps(data))

    def run(self):
        self.event_loop.run_forever()


webrtc_client = WebRtcClient()
webrtc_client.start()
