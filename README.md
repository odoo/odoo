# Odoo Room Booking Module

## Introduction

This module is developed to manage room reservations within a company. It allows employees to book meeting rooms and administrators to manage room availability and confirm reservations.

## Installation

### Prerequisites

- PyCharm Community Edition
- Python 3.10.11
- Visual Studio Build Tools 2022

### Setup

1. Install the required Python version and set it as the default interpreter in PyCharm.
2. Clone the Odoo 17 repository:

```bash
git clone https://www.github.com/odoo/odoo --depth 1 --branch 17.0 --single-branch odoo17
```

3. Install the necessary dependencies from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

4. Create a superuser in pgAdmin4 named `odoo17` with password `odoo17` and all privileges.
5. Configure the `odoo.conf` file with the absolute paths of the addons folder and the login of the superuser `odoo17`.
6. Set the `odoo17` folder as the root directory and launch the application.
7. Go to `localhost:8069` to create a new database named `admin`.

## Module Description

The module adds the following functionalities:

- **Room Management**: Define and manage meeting rooms.
- **Reservation Management**: Employees can book rooms, and administrators can confirm or cancel reservations.
- **Database Integration**: Tables for rooms and reservations are created and managed.
- **Role-based Access**: Different roles for employees and administrators with specific permissions.
- **Automated Processes**: Reservation and confirmation processes are automated.

## Adding the Module

1. Add a folder called `custom_addons` with the following structure:

- `models/`: Contains the Python models for the module.
- `views/`: Contains the XML files for the module's interface.
- `security/`: Contains the security rules for the module.
- `__manifest__.py`: The manifest file describing the module.

2. Update the `odoo.conf` file to include the `custom_addons` folder in the `addon_path`.
3. Define models for rooms (`salle.py`) and reservations (`reservation.py`).
4. Create views for rooms and reservations (`salle_view.xml` and `reservation_view.xml`).
5. Update the security rules in `ir.model.access.csv` to grant appropriate access rights to the module.
6. Add the created files to the `__manifest__.py` file.

## Testing

1. Launch the application and navigate to the Room Booking module.
2. Test adding rooms and making reservations.
3. Verify that the constraints are enforced, such as the end date being after the start date and the room being available for the requested time.

## Contributor

- Asma Hachaichi
