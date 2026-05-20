### Test 1: The Master Data Fetch (JIT Token & API Trigger)

**Goal:** Prove the "Fetch Category" button works, triggers the JIT Token fetch, and catches API errors elegantly.

1. Go to **Settings -> General Settings** (or the Company form) and enter dummy strings for the Baiwang App Key, App Secret, and Salt.
2. Go to **Inventory / Sales -> Products** and open any product.
3. Go to your new *China Golden Tax (Baiwang)* section on the General Information tab.
4. Click **"Fetch Category from Baiwang"**.
5. **Expected Result:** Odoo should show a Red `UserError` pop-up saying something like *"Failed to authenticate with Baiwang API"* or *"Network error while refreshing token"*.
*(If you see this, your `baiwang_client.py` and token management are working!)*

### Test 2: The Synchronous Invoice Issuance (Send & Print Hook)

**Goal:** Prove that the Send & Print wizard correctly hooks into the Baiwang client before generating the PDF.

1. Go to **Accounting -> Customer Invoices** and create a new invoice.
2. Ensure the Customer's country is set to **China (CN)**. Add a product and a price, then click **Confirm**.
3. Click the **Send & Print** button at the top of the invoice.
4. **Expected Result 1:** The wizard pops up. You should see your new **"Issue E-Fapiao (Baiwang)"** checkbox, and it should be checked by default.
5. Click **Send** on the wizard.
6. **Expected Result 2:** Odoo will pause, try to call Baiwang, and throw an error like *"Baiwang Issuance Failed: [Error Message]"*. The invoice will remain Confirmed, but no PDF will be generated and no Fapiao number will be saved.
*(If you see this, your `account_move_send` wizard override is flawless and protecting the database from network rollbacks!)*

### Test 3: The Asynchronous Red Form Flow (State Machine)

**Goal:** Prove the Credit Note UI logic and the background Cron job configuration.

1. Go to **Accounting -> Customer Invoices** and create a **Credit Note**. Leave it in the `Draft` state.
2. Ensure the customer's country is **China (CN)**.
3. **Expected Result 1:** You should see your blue **"Request Baiwang Red Form"** button in the header.
4. Click the button.
5. **Expected Result 2:** Depending on how Baiwang's API handles your dummy token, you will either get an immediate error pop-up, OR the document state in the *China E-Fapiao* tab will change to **Failed/Rejected**.
6. **To test the Cron job:** Go to **Settings -> Technical -> Scheduled Actions** (make sure Developer Mode is on). Search for *Baiwang: Check Pending Red Forms*. Click into it and click **Run Manually**.
*(Check your terminal/server log. You should see a log message saying `Baiwang EDI: Found 0 pending red forms. Polling for status...` or similar, proving the cron job executed without crashing!)*
