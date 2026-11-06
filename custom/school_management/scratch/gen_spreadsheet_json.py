import json

dashboard = {
    "version": "18.5.10",
    "sheets": [
        {
            "id": "sheet1",
            "name": "Academic Analytics",
            "colNumber": 9,
            "rowNumber": 40,
            "rows": {
                "0": {"size": 36},
                "1": {"size": 24},
                "3": {"size": 28},
                "4": {"size": 28},
                "17": {"size": 28},
                "18": {"size": 28}
            },
            "cols": {
                "0": {"size": 140},
                "1": {"size": 180},
                "2": {"size": 200},
                "3": {"size": 200},
                "4": {"size": 120},
                "5": {"size": 120},
                "6": {"size": 140},
                "7": {"size": 120}
            },
            "merges": [
                "A1:H1",
                "A2:H2"
            ],
            "cells": {
                "A1": "HARVARD UNIVERSITY - EXECUTIVE ACADEMIC & STUDENT PERFORMANCE DASHBOARD",
                "A2": "Institutional overview of enrolled student achievement, degree distribution, and course examination results.",
                
                # Section 1 Header
                "A4": "TOP STUDENTS BY CUMULATIVE GPA & ACADEMIC STANDING",
                
                # Section 1 Table Headers (Row 5)
                "A5": '=ODOO.LIST.HEADER(1, "student_id", _t("Student ID"))',
                "B5": '=ODOO.LIST.HEADER(1, "name", _t("Student Name"))',
                "C5": '=ODOO.LIST.HEADER(1, "program_id", _t("Degree Program"))',
                "D5": '=ODOO.LIST.HEADER(1, "department_id", _t("Department"))',
                "E5": '=ODOO.LIST.HEADER(1, "gpa", _t("GPA"))',
                "F5": '=ODOO.LIST.HEADER(1, "attendance_rate", _t("Attendance %"))',
                "G5": '=ODOO.LIST.HEADER(1, "status", _t("Status"))',
                
                # Section 2 Header
                "A18": "COURSE EXAMINATIONS & CLASS PERFORMANCE OVERVIEW",
                
                # Section 2 Table Headers (Row 19)
                "A19": '=ODOO.LIST.HEADER(2, "name", _t("Examination Title"))',
                "B19": '=ODOO.LIST.HEADER(2, "subject_id", _t("Course / Subject"))',
                "C19": '=ODOO.LIST.HEADER(2, "section_id", _t("Class Section"))',
                "D19": '=ODOO.LIST.HEADER(2, "teacher_id", _t("Instructor"))',
                "E19": '=ODOO.LIST.HEADER(2, "exam_type", _t("Type"))',
                "F19": '=ODOO.LIST.HEADER(2, "exam_date", _t("Exam Date"))',
                "G19": '=ODOO.LIST.HEADER(2, "average_score", _t("Class Average"))',
                "H19": '=ODOO.LIST.HEADER(2, "state", _t("Status"))',
            },
            "styles": {
                "A1": 1,
                "A2": 2,
                "A4": 3,
                "A5:G5": 4,
                "A18": 3,
                "A19:H19": 4,
            },
            "formats": {},
            "borders": {
                "A1:H1": 1,
                "A5:G5": 2,
                "A19:H19": 2,
            },
            "conditionalFormats": [],
            "dataValidationRules": [],
            "figures": [],
            "tables": [
                {
                    "range": "A5:G15",
                    "type": "static",
                    "config": {
                        "hasFilters": False,
                        "totalRow": False,
                        "firstColumn": False,
                        "lastColumn": False,
                        "numberOfHeaders": 1,
                        "bandedRows": True,
                        "bandedColumns": False,
                        "automaticAutofill": True,
                        "styleId": "None"
                    }
                },
                {
                    "range": "A19:H29",
                    "type": "static",
                    "config": {
                        "hasFilters": False,
                        "totalRow": False,
                        "firstColumn": False,
                        "lastColumn": False,
                        "numberOfHeaders": 1,
                        "bandedRows": True,
                        "bandedColumns": False,
                        "automaticAutofill": True,
                        "styleId": "None"
                    }
                }
            ],
            "areGridLinesVisible": True,
            "isVisible": True,
            "headerGroups": {
                "ROW": [],
                "COL": []
            },
            "comments": {}
        }
    ],
    "styles": {
        "1": {"fontSize": 14, "bold": True, "fillColor": "#1B365D", "textColor": "#FFFFFF", "align": "center", "verticalAlign": "middle"},
        "2": {"fontSize": 10, "italic": True, "fillColor": "#F1F5F9", "textColor": "#475569", "align": "center", "verticalAlign": "middle"},
        "3": {"fontSize": 11, "bold": True, "textColor": "#1B365D", "verticalAlign": "middle"},
        "4": {"fontSize": 10, "bold": True, "fillColor": "#F8FAFC", "textColor": "#1E293B", "verticalAlign": "middle"},
    },
    "formats": {},
    "borders": {
        "1": {"bottom": {"style": "thick", "color": "#1B365D"}},
        "2": {"bottom": {"style": "thin", "color": "#CBD5E1"}, "top": {"style": "thin", "color": "#CBD5E1"}},
    },
    "revisionId": "START_REVISION",
    "uniqueFigureIds": True,
    "settings": {
        "locale": {
            "name": "English (US)",
            "code": "en_US",
            "thousandsSeparator": ",",
            "decimalSeparator": ".",
            "dateFormat": "mm/dd/yyyy",
            "timeFormat": "hh:mm:ss",
            "formulaArgSeparator": ",",
            "weekStart": 7
        }
    },
    "pivots": {},
    "pivotNextId": 1,
    "globalFilters": [],
    "lists": {
        "1": {
            "columns": [
                "student_id",
                "name",
                "program_id",
                "department_id",
                "gpa",
                "attendance_rate",
                "status"
            ],
            "domain": [],
            "model": "university.student",
            "context": {},
            "orderBy": [
                {"name": "gpa", "desc": True}
            ],
            "id": "1",
            "name": "Top Students by GPA"
        },
        "2": {
            "columns": [
                "name",
                "subject_id",
                "section_id",
                "teacher_id",
                "exam_type",
                "exam_date",
                "average_score",
                "state"
            ],
            "domain": [],
            "model": "university.exam",
            "context": {},
            "orderBy": [
                {"name": "exam_date", "desc": True}
            ],
            "id": "2",
            "name": "Course Examinations"
        }
    },
    "listNextId": 3,
    "chartOdooMenusReferences": {}
}

# Add rows 6 to 15 for List 1 (Students)
for r in range(6, 16):
    row_idx = r - 5
    dashboard["sheets"][0]["cells"][f"A{r}"] = f'=ODOO.LIST(1, {row_idx}, "student_id")'
    dashboard["sheets"][0]["cells"][f"B{r}"] = f'=ODOO.LIST(1, {row_idx}, "name")'
    dashboard["sheets"][0]["cells"][f"C{r}"] = f'=ODOO.LIST(1, {row_idx}, "program_id")'
    dashboard["sheets"][0]["cells"][f"D{r}"] = f'=ODOO.LIST(1, {row_idx}, "department_id")'
    dashboard["sheets"][0]["cells"][f"E{r}"] = f'=ODOO.LIST(1, {row_idx}, "gpa")'
    dashboard["sheets"][0]["cells"][f"F{r}"] = f'=ODOO.LIST(1, {row_idx}, "attendance_rate")'
    dashboard["sheets"][0]["cells"][f"G{r}"] = f'=ODOO.LIST(1, {row_idx}, "status")'

# Add rows 20 to 29 for List 2 (Exams)
for r in range(20, 30):
    row_idx = r - 19
    dashboard["sheets"][0]["cells"][f"A{r}"] = f'=ODOO.LIST(2, {row_idx}, "name")'
    dashboard["sheets"][0]["cells"][f"B{r}"] = f'=ODOO.LIST(2, {row_idx}, "subject_id")'
    dashboard["sheets"][0]["cells"][f"C{r}"] = f'=ODOO.LIST(2, {row_idx}, "section_id")'
    dashboard["sheets"][0]["cells"][f"D{r}"] = f'=ODOO.LIST(2, {row_idx}, "teacher_id")'
    dashboard["sheets"][0]["cells"][f"E{r}"] = f'=ODOO.LIST(2, {row_idx}, "exam_type")'
    dashboard["sheets"][0]["cells"][f"F{r}"] = f'=ODOO.LIST(2, {row_idx}, "exam_date")'
    dashboard["sheets"][0]["cells"][f"G{r}"] = f'=ODOO.LIST(2, {row_idx}, "average_score")'
    dashboard["sheets"][0]["cells"][f"H{r}"] = f'=ODOO.LIST(2, {row_idx}, "state")'

with open("custom/school_management/data/files/academic_dashboard.json", "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2)

print("Created custom/school_management/data/files/academic_dashboard.json successfully!")
