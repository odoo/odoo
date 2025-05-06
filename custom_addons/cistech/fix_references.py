#!/usr/bin/env python3
import os
import re
import sys

# Получаем абсолютный путь к директории скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))

def replace_in_file(file_path):
    """Заменяет все ссылки на multi_vendor_marketplace на cistech в файле"""
    print(f"Processing file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Заменяем ссылки на группы и модули
        modified = content.replace('multi_vendor_marketplace.', 'cistech.')
        
        # Заменяем ссылки на иконки
        modified = modified.replace('web_icon="multi_vendor_marketplace,', 'web_icon="cistech,')
        
        # Заменяем ссылки на параметры ir.config_parameter
        modified = re.sub(
            r"get_param\('multi_vendor_marketplace\.",
            r"get_param('cistech.",
            modified
        )
        
        # Заменяем ID шаблонов
        modified = re.sub(
            r'<template id="multi_vendor_marketplace\.',
            r'<template id="cistech.',
            modified
        )
        
        # Заменяем ссылки на шаблоны
        modified = re.sub(
            r't-call="multi_vendor_marketplace\.',
            r't-call="cistech.',
            modified
        )
        
        if content != modified:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(modified)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_references(directory):
    """Обходит все XML файлы в директории и заменяет ссылки"""
    directory_path = os.path.join(script_dir, directory)
    print(f"Processing directory: {directory_path}")
    
    if not os.path.exists(directory_path):
        print(f"Directory not found: {directory_path}")
        return
    
    count = 0
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.xml'):
                file_path = os.path.join(root, file)
                if replace_in_file(file_path):
                    count += 1
                    print(f"Updated: {file_path}")
    print(f"Total files updated in {directory}: {count}")

if __name__ == '__main__':
    print(f"Script running from: {script_dir}")
    
    # Путь к директории views
    views_dir = 'views'
    fix_references(views_dir)
    
    # Также проверяем файлы в security и data
    security_dir = 'security'
    fix_references(security_dir)
    
    data_dir = 'data'
    fix_references(data_dir)
    
    # Также проверяем файлы в custom directory
    custom_dir = 'custom'
    fix_references(custom_dir) 