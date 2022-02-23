# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

import imutils
import cv2
import os
import logging
_logger = logging.getLogger(__name__)

try:
    from pikepdf import Pdf, PdfImage
    import qrtools
    imported = True
except ImportError:
    _logger.warning("`pikepdf` and/or `qrtools` Python modules not found, bill prefiling disabled. "
                    "Consider installing those modules if you want your QR-Bills to be prepopulated.")
    imported = False

_extracted_img_path = 'extracted.png'
_extracted_img_name = 'extracted'
_cropped_img_path = 'cropped.jpg'
_masked_qr_path = 'mask.jpg'
temp_images_path = [_extracted_img_path, _extracted_img_name, _cropped_img_path, _masked_qr_path]


def _qr_decode(path_qr):
    """
    Takes an isolated QR image and returns the data it contains
    """
    qr = qrtools.QR()
    qr.decode(path_qr)
    return qr.data

# ========================================== Image Manipulation ===========================================
def _prepare_image_for_search(img_path):
    """
    Returns a version of the parameter image that's black and white and 'edged'. This makes the comparison between
    images easier.
    """
    read = cv2.imread(img_path)
    gray = cv2.cvtColor(read, cv2.COLOR_BGR2GRAY)
    edged = cv2.Canny(gray, 50, 200)
    return edged


def _crop_img(img_path):
    # If the document is not already an image extracted from a pdf, we need to crop it to only keep the QR part.
    # Since the QR bill format is very rigid, we can approximate its position and size.
    # This is however bound to be less reliable than the pdf version.
    img = cv2.imread(img_path)
    height, width = img.shape[:2]
    result_img = img[int(height / 1.42):int(height / 1.16), int(width / 3.15):int(width / 1.85)]
    cv2.imwrite(_cropped_img_path, result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 100]),
    return _cropped_img_path


def _resize_template(template, img_width):
    """
    Resize the swiss cross template image to correspond to the size of the image in which it needs to be searched.
    params :
        template : the path to the swiss qr cross image
        img_width : the width of the image in which the swiss cross can be found
    """
    resized_template = imutils.resize(template, width=int(img_width))
    resized_template = imutils.resize(resized_template, width=int(img_width / 6.62))
    return resized_template


def _find_and_hide_swiss_cross(template_path='addons/l10n_ch/static/src/img/CH-Cross_7mm.png', img_path=""):
    """
    The decorative swiss cross in the middle of the QR code makes it impossible for the qr reader to extract data.
    This function tries to find the cross in the image and to apply an empty rectangle over it to allow for the reading.

    params :    template_path : the path to the swiss cross image
                img_path : the path to the full page image potentially containing a swiss QR code

    returns : if the masking succeeds, returns the path to an image having its swiss cross hidden
    """
    if img_path == "":
        return False
    try:

        # if not is_pdf:
        #     img = cv2.imread(img_path)
        #     height, width = img.shape[:2]
        #     result_img = img[int(height/1.42):int(height/1.16), int(width/3.15):int(width/1.85)]
        #     cv2.imwrite(_cropped_img_path, result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 100]),
        #     img_path = _cropped_img_path
        # Prepare the files for the search
        edged_image = _prepare_image_for_search(img_path)
        edged_template = _prepare_image_for_search(template_path)
        # Resize the template proportionally to the QR image
        resized_template = _resize_template(template=edged_template, img_width=edged_image.shape[1])
        # Attempt to find the template in the image
        result = cv2.matchTemplate(edged_image, resized_template, cv2.TM_CCOEFF)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        height, width = resized_template.shape[:2]
        top_left = max_loc
        bottom_right = (top_left[0] + width, top_left[1] + height)
        result_img = cv2.rectangle(cv2.imread(img_path), top_left, bottom_right, (255, 255, 255), -1)
        # Save result
        cv2.imwrite(_masked_qr_path, result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 100]),
        return _masked_qr_path
    except cv2.error:
        return False

# ============================================ Data Extraction ============================================
def check_content_respects_guidelines(content_list):
    """
    Checks that the data extracted from the QR code are correct at first glance,
    by checking some required fields with a fixed value.
    """
    return len(content_list) == 31 and content_list[0] == 'SPC' and content_list[2] == '1' and content_list[30] == 'EPD'


def extract_structured_addresses_infos(bill_infos, qr_content_list):
    """
    Extract creditor and debtor's addresses if either correspond to the S format
    (see SIX documentation)
    """
    if bill_infos['creditor_address_type'] == 'S':
        bill_infos['creditor_street'] = qr_content_list[6]
        bill_infos['creditor_house_nb'] = qr_content_list[7]
        bill_infos['creditor_post_code'] = qr_content_list[8]
        bill_infos['creditor_town'] = qr_content_list[9]
    if bill_infos['debtor_address_type'] == 'S':
        bill_infos['debtor_street'] = qr_content_list[22]
        bill_infos['debtor_house_nb'] = qr_content_list[23]
        bill_infos['debtor_post_code'] = qr_content_list[24]
        bill_infos['debtor_town'] = qr_content_list[25]
    return bill_infos


def extract_combined_addresses_infos(bill_infos, qr_content_list):
    """
    Extract creditor and debtor's addresses if either correspond to the K format
    (see SIX documentation)
    """
    if bill_infos['creditor_address_type'] == 'K':
        bill_infos['creditor_street_1'] = qr_content_list[6]
        bill_infos['creditor_street_2'] = qr_content_list[7]
    if bill_infos['debtor_address_type'] == 'K':
        bill_infos['debtor_street_1'] = qr_content_list[22]
        bill_infos['debtor_street_2'] = qr_content_list[23]
    return bill_infos


def transform_raw_data(raw_data):
    """
    Creates a comprehensible map thanks to the informations extracted from the QR code.
    """
    qr_info_index = {
        'iban': 3,
        'creditor_address_type': 4,
        'creditor_name': 5,
        'creditor_country_code': 10,
        'amount': 18,
        'currency': 19,
        'debtor_address_type': 20,
        'debtor_name': 21,
        'debtor_country_code':26,
        'reference_type': 27,
        'reference': 28,
        'communication': 29
    }
    qr_content_list = raw_data.splitlines()
    bill_infos = {}
    # Documentation can be found on the SIX implementation guideline.
    # https://www.six-group.com/dam/download/banking-services/interbank-clearing/fr/standardization/iso/swiss-recommendations/implementation-guidelines-ct-2022.pdf
    content_readable = check_content_respects_guidelines(qr_content_list)
    if content_readable:
        for key in qr_info_index:
            bill_infos[key] = qr_content_list[qr_info_index[key]]
        bill_infos = extract_structured_addresses_infos(bill_infos=bill_infos, qr_content_list=qr_content_list)
        bill_infos = extract_combined_addresses_infos(bill_infos=bill_infos, qr_content_list=qr_content_list)
    return bill_infos


def extract_data_from(img_containing_qr):
    """
    From an image containing a QR, returns a dic indicating info_title --> info_contained_in_qr, if possible.
    """
    path_to_modified_qr = _find_and_hide_swiss_cross(img_path=img_containing_qr)
    if path_to_modified_qr:
        raw_data = _qr_decode(path_to_modified_qr)
        if raw_data and raw_data != "NULL":
            return transform_raw_data(raw_data)


def delete_temp_images():
    """
    Checks that the path registered in temp_images_path exist.
    If so, deletes them.
    """
    for to_del in temp_images_path:
        if to_del and os.path.exists(to_del):
            os.remove(to_del)


class QrBillReader(models.Model):
    _name = "qrbillreader"
    _description = "A tool allowing to prefill the bill fields when they are imported in l10n_ch, thanks to the " \
                   "mandatory QR-Code on it."

    def read_qr_content(self, path_to_file, file_format):
        """Takes the path to a pdf file and returns a dict of the information contained on the QR code in the pdf.
            If any steps goes wrong, returns an empty map
        """
        if not imported:
            return {}
        transformed_data = {}
        try:
            if 'pdf' in file_format:
                pdf = Pdf.open(path_to_file)
                # if the doc is a QR bill, the QR is likely to be on the last page.
                page = pdf.pages[len(pdf.pages) - 1]
                for img_index in page.images:
                    pdf_image = PdfImage(page.images[img_index])
                    pdf_image.extract_to(fileprefix=_extracted_img_name)
                    transformed_data = extract_data_from(_extracted_img_path)
                    if transformed_data:
                        break
            else:
                cropped_img = _crop_img(path_to_file)
                transformed_data = extract_data_from(img_containing_qr=cropped_img)
        finally:
            delete_temp_images()
        return transformed_data
