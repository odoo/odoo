
Cutom Odooship Password Policy
=============================
The Password Policy module enforces customizable password security rules, including strength requirements, expiration notifications, and password history restrictions, ensuring enhanced authentication security in Odoo.

Features
========
* The Password Policy module is designed to integrate seamlessly with Odoo’s authentication framework, providing administrators with robust controls to enforce password security standards. Below is an overview of its functionality as described in the manifest:

1) Security Enforcement:Allows administrators to set comprehensive password requirements—such as minimum length, complexity, and character rules—to ensure that user passwords meet high-security standards.

2) Signup Integration: Enhances the user registration process by integrating password policies into the signup templates. This ensures that new users create compliant passwords from the outset.

3) Automated Notifications:Utilizes scheduled cron jobs to send timely email notifications to users as their passwords approach expiration. This proactive measure helps maintain strong, up-to-date credentials.

4) Password History Management:Implements mechanisms to track and restrict the reuse of previous passwords, thereby minimizing vulnerabilities associated with repeated credentials.

5) Administrative Configuration: Offers intuitive views within Odoo’s settings, enabling administrators to customize and adjust password policies, notification intervals, and security parameters according to organizational needs.

Configuration
=============
1) Password Expiration: Administrators can set a time period after which users must change their passwords. By default, passwords expire after 90 days.

2) Password History Restriction: Prevents users from reusing previously used passwords, enhancing security by enforcing a unique password policy.

3) Password Complexity Requirements:

- Minimum number of lowercase characters required in a password.
- Minimum number of uppercase characters required in a password.
- Minimum number of numeric digits required in a password.
- Minimum number of special characters required in a password.
- Test Mode for Password Expiration: Converts the expiration period from days to minutes, making it easier for administrators to test policy enforcement without waiting for long durations.

4) Password Expiration Time Computation: Allows customization of how expiration times are calculated, providing flexibility in policy enforcement.

5) Password Expiry Alerts: Sends notifications to users a specified number of days before their password expires, prompting them to update their credentials in advance.

These configurable settings provide a comprehensive password policy framework to strengthen authentication security within Odoo.


Credits
-------
* Developers: (v17) Drishti Joshi


