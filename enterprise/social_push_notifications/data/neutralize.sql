-- Unset Firebase configuration within website
UPDATE website
   SET firebase_enable_push_notifications = false,
       firebase_use_own_account = false,
       firebase_project_id = NULL,
       firebase_web_api_key = NULL,
       firebase_push_certificate_key = NULL,
       firebase_sender_id = NULL;
