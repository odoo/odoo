import smtplib, ssl
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_receive_booking_email(email_booking_data):
    sender_email = email_booking_data['sender_email']
    password = email_booking_data['sender_pass']
    receiver_email = email_booking_data['receiver_email']
    smtp_host = email_booking_data['smtp_host']
    smtp_port = email_booking_data['smtp_port']

    message = MIMEMultipart("alternative")
    message["Subject"] = "NEW BOOKING !"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Convert UTC Time Zone to Local Phnom Penh Time Zone
    # This block of function might not included if timzone configuration is right when deployed 
    utc_time = datetime.now()
    tz = pytz.timezone('Asia/Phnom_Penh')
    local_pp_time = pytz.utc.localize(utc_time, is_dst=None).astimezone(tz)
    # This block of function might not included if timzone configuration is right when deployed 
    # Convert UTC Time Zone to Local Phnom Penh Time Zone
    
    # Create the plain-text and HTML version of your message
    html = """\
    <html>
    <body>
        <ul>
            <li> Created Booking Date : {0}</li><br>
            <li> Court : <b>{1}</b></li><br>
            <li> Booking Time : <b>{2}</b></li><br>
            <li> Duration : <b>{3}</b></li><br>
            <li> Customer Name : <b>{4}</b></li><br>
            <li> Phone Number : <b>{5}</b></li><br>
        </ul>
    </body>
    </html>
    """.format(local_pp_time,email_booking_data['chair_name'],
    email_booking_data['time'],email_booking_data['duration'],email_booking_data['name'],
    email_booking_data['phone'])

    # Turn these into plain/html MIMEText objects
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part2)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )

# send_receive_booking_email("yinmazatin00@gmail.com")


