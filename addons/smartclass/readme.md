===========================
Testing Smartclass Exercise
===========================

We have created a mini application with:
- A `Volume` model
- A JavaScript function `formatHumanReadable`
- A `HumanReadableWidget` that uses the `formatHumanReadable` function

You are asked to:

1. **Create a file `/tests/test_volume.py`**  
   - This file should test the Python model  
   - Create records and verify that `.volume` and `.category` return the expected values

2. **Create a file `/static/tests/human_readable.test.js`**  
   - This file should test the `formatHumanReadable` function  
   - It should also test the `HumanReadableWidget`

3. **Add an integration test in `/tests/test_volume.py`**  
   - Create a test that inserts records into the database  
   - Verify that the records have been correctly added and that the data is correct  
   - You will need to create a file `/static/tests/tours/create_volume.js` to write the tour in it

---

## Running the Tests

### Install Module

```bash
./odoo-bin --config=../.vscode/odoo.conf -i smartclass
```

### Python Unit Tests

```bash
./odoo-bin --config=../.vscode/odoo.conf --test-enable --test-tags=.test_volume_model
```

### JavaScript Unit Test (Hoot)

Run the Odoo server for JS tests:

```bash
./odoo-bin --config=../.vscode/odoo.conf
```

Then, open your browser and navigate to:

```
http://localhost:8069/web/tests?debug=assets
```

### Integration Tests

```bash
./odoo-bin --config=../.vscode/odoo.conf --test-enable --test-tags=.test_tour_create_volumes
```

You can add `debug=1` to the `start_tour` method to run the tour in debug mode.
