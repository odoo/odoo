# more details about the codes can be seen
# on the following link: https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/

BOUNCED_ERROR_CODES = {
    131026,  # Unable to deliver message. One of the reasons: The recipient phone number is not a WhatsApp phone number.
    131045,  # Message failed to send due to a phone number registration error.
    131049,  # This message was not delivered to maintain healthy ecosystem engagement.
    131051,  # Unsupported message type.
    131052,  # Unable to download the media sent by the user.
    131053,  # Unable to upload the media used in the message.
    131030,  # For testing and reproducibility purposes only
}
