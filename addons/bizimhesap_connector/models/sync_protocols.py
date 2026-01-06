# -*- coding: utf-8 -*-
"""
Senkronizasyon Eşleştirme ve Çakışma Çözüm Protokolleri
=======================================================
Tüm sistemler için standart eşleştirme kuralları:
- BizimHesap ↔ Odoo Community
- Odoo Community ↔ Odoo Enterprise

Kurallar:
- Ürün: Barkod > Ürün Kodu (varyant) > İsim (%50)
- Cari: VKN > Telefon > E-posta > İsim (%50) + Şube tespiti
- Son güncellenen veri kazanır (Last Write Wins)
"""

import re
from datetime import datetime
from difflib import SequenceMatcher
import logging

_logger = logging.getLogger(__name__)


class SyncProtocols:
    """Senkronizasyon Eşleştirme Protokolleri"""
    
    # ═══════════════════════════════════════════════════════════════
    # YAPILANDIRMA
    # ═══════════════════════════════════════════════════════════════
    
    PRODUCT_NAME_SIMILARITY_THRESHOLD = 0.50  # %50
    PARTNER_NAME_SIMILARITY_THRESHOLD = 0.50  # %50
    BRANCH_NAME_SIMILARITY_THRESHOLD = 0.80   # %80 - Şube tespiti için
    CATEGORY_SIMILARITY_THRESHOLD = 0.80      # %80
    
    # Öncelik sırası (çakışma durumunda)
    SYSTEM_PRIORITY = {
        'enterprise': 1,  # En yüksek öncelik
        'community': 2,
        'bizimhesap': 3,
        'external': 4,    # En düşük öncelik
    }
    
    # Türkiye şehirleri (şube tespiti için)
    TURKEY_CITIES = [
        'adana', 'adıyaman', 'afyon', 'ağrı', 'aksaray', 'amasya', 'ankara', 'antalya',
        'ardahan', 'artvin', 'aydın', 'balıkesir', 'bartın', 'batman', 'bayburt',
        'bilecik', 'bingöl', 'bitlis', 'bolu', 'burdur', 'bursa', 'çanakkale',
        'çankırı', 'çorum', 'denizli', 'diyarbakır', 'düzce', 'edirne', 'elazığ',
        'erzincan', 'erzurum', 'eskişehir', 'gaziantep', 'giresun', 'gümüşhane',
        'hakkari', 'hatay', 'ığdır', 'isparta', 'istanbul', 'izmir', 'kahramanmaraş',
        'karabük', 'karaman', 'kars', 'kastamonu', 'kayseri', 'kırıkkale', 'kırklareli',
        'kırşehir', 'kilis', 'kocaeli', 'konya', 'kütahya', 'malatya', 'manisa',
        'mardin', 'mersin', 'muğla', 'muş', 'nevşehir', 'niğde', 'ordu', 'osmaniye',
        'rize', 'sakarya', 'samsun', 'siirt', 'sinop', 'sivas', 'şanlıurfa', 'şırnak',
        'tekirdağ', 'tokat', 'trabzon', 'tunceli', 'uşak', 'van', 'yalova', 'yozgat',
        'zonguldak'
    ]
    
    # İstanbul ilçeleri
    ISTANBUL_DISTRICTS = [
        'adalar', 'arnavutköy', 'ataşehir', 'avcılar', 'bağcılar', 'bahçelievler',
        'bakırköy', 'başakşehir', 'bayrampaşa', 'beşiktaş', 'beykoz', 'beylikdüzü',
        'beyoğlu', 'büyükçekmece', 'çatalca', 'çekmeköy', 'esenler', 'esenyurt',
        'eyüp', 'eyüpsultan', 'fatih', 'gaziosmanpaşa', 'güngören', 'kadıköy',
        'kağıthane', 'kartal', 'küçükçekmece', 'maltepe', 'pendik', 'sancaktepe',
        'sarıyer', 'silivri', 'sultanbeyli', 'sultangazi', 'şile', 'şişli',
        'tuzla', 'ümraniye', 'üsküdar', 'zeytinburnu'
    ]
    
    # ═══════════════════════════════════════════════════════════════
    # TARİH KARŞILAŞTIRMA - EN GÜNCEL VERİ KAZANIR
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def parse_datetime(dt_value):
        """Farklı formatlardaki tarihleri datetime objesine çevir"""
        if not dt_value:
            return None
        if isinstance(dt_value, datetime):
            return dt_value
        if isinstance(dt_value, str):
            for fmt in [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d',
                '%d.%m.%Y %H:%M:%S',
                '%d.%m.%Y',
            ]:
                try:
                    return datetime.strptime(dt_value.split('+')[0].split('Z')[0], fmt)
                except ValueError:
                    continue
        return None
    
    @classmethod
    def get_winner(cls, records_with_dates):
        """
        En güncel kaydı belirle (Last Write Wins)
        
        Args:
            records_with_dates: [
                {'data': {...}, 'write_date': '2025-12-29 14:30:00', 'system': 'community'},
                {'data': {...}, 'write_date': '2025-12-28 10:00:00', 'system': 'enterprise'},
            ]
        
        Returns:
            dict: Kazanan kayıt
        """
        if not records_with_dates:
            return None
        
        winner = None
        winner_date = None
        winner_priority = 999
        
        for record in records_with_dates:
            record_date = cls.parse_datetime(record.get('write_date'))
            system = record.get('system', 'external')
            priority = cls.SYSTEM_PRIORITY.get(system, 4)
            
            if record_date is None:
                continue
            
            # Tarih daha yeni mi?
            if winner_date is None or record_date > winner_date:
                winner = record
                winner_date = record_date
                winner_priority = priority
            # Tarih aynı ise önceliğe bak
            elif record_date == winner_date and priority < winner_priority:
                winner = record
                winner_priority = priority
        
        return winner
    
    @classmethod
    def is_source_newer(cls, source_date, target_date):
        """Kaynak hedeften daha güncel mi?"""
        source_dt = cls.parse_datetime(source_date)
        target_dt = cls.parse_datetime(target_date)
        
        if source_dt is None:
            return False
        if target_dt is None:
            return True
        return source_dt > target_dt
    
    # ═══════════════════════════════════════════════════════════════
    # YARDIMCI FONKSİYONLAR
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def normalize_phone(phone):
        """Telefon numarasını normalize et: +90 5XX XXX XXXX"""
        if not phone:
            return None
        digits = re.sub(r'\D', '', str(phone))
        if digits.startswith('90') and len(digits) == 12:
            return '+' + digits
        elif digits.startswith('0') and len(digits) == 11:
            return '+9' + digits
        elif len(digits) == 10 and digits.startswith('5'):
            return '+90' + digits
        elif len(digits) == 10:
            return '+90' + digits
        return '+' + digits if digits else None
    
    @staticmethod
    def normalize_vat(vat):
        """Vergi numarasını normalize et"""
        if not vat:
            return None
        digits = re.sub(r'\D', '', str(vat))
        if len(digits) in (10, 11):
            return digits
        return digits if digits else None
    
    @staticmethod
    def normalize_company_name(name):
        """Firma adını normalize et (karşılaştırma için)"""
        if not name:
            return ''
        name = name.lower().strip()
        # Şirket eklentilerini kaldır
        suffixes = [
            'ltd.', 'ltd', 'limited', 'şti.', 'şti', 'sti.', 'sti',
            'a.ş.', 'a.ş', 'aş', 'as', 'anonim şirketi', 'anonim sirketi',
            'tic.', 'tic', 'ticaret', 'san.', 'san', 'sanayi',
            'paz.', 'paz', 'pazarlama', 'ltd. şti.', 'ltd. sti.',
            'inc.', 'inc', 'corp.', 'corp', 'llc', 'gmbh',
            've', 'veya', '&'
        ]
        for suffix in suffixes:
            name = name.replace(suffix, ' ')
        # Fazla boşlukları temizle
        name = ' '.join(name.split())
        return name
    
    @staticmethod
    def normalize_barcode(barcode):
        """Barkodu normalize et"""
        if not barcode:
            return None
        barcode = str(barcode).strip()
        barcode = re.sub(r'[^a-zA-Z0-9]', '', barcode)
        return barcode if barcode else None
    
    @staticmethod
    def normalize_product_code(code):
        """Ürün kodunu normalize et"""
        if not code:
            return None
        code = str(code).strip().upper()
        return code if code else None
    
    @staticmethod
    def calculate_similarity(str1, str2):
        """İki string arasındaki benzerlik oranı (0-1)"""
        if not str1 or not str2:
            return 0.0
        str1 = str(str1).lower().strip()
        str2 = str(str2).lower().strip()
        return SequenceMatcher(None, str1, str2).ratio()
    
    @classmethod
    def extract_location_from_address(cls, address, city=None):
        """Adresten şehir/ilçe bilgisi çıkar"""
        if not address and not city:
            return None
        
        text = f"{address or ''} {city or ''}".lower()
        
        # Önce İstanbul ilçelerini kontrol et
        for district in cls.ISTANBUL_DISTRICTS:
            if district in text:
                return district.title()
        
        # Sonra şehirleri kontrol et
        for city_name in cls.TURKEY_CITIES:
            if city_name in text:
                return city_name.title()
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # ÜRÜN EŞLEŞTİRME PROTOKOLܠ
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def match_product(cls, source_product, target_products):
        """
        Ürün eşleştirme protokolü
        
        Öncelik:
        1. Barkod eşleşmesi → Kesin eşleşme
        2. Ürün kodu aynı + Barkod farklı → Varyant
        3. Ürün kodu aynı → Kesin eşleşme
        4. İsim benzerliği ≥%50 → Benzer eşleşme
        
        Returns:
            dict: {
                'match_type': 'exact' | 'variant' | 'similar' | 'new',
                'matched_product': product or None,
                'matched_template_id': int or None,
                'similarity': float,
                'reason': str
            }
        """
        source_barcode = cls.normalize_barcode(source_product.get('barcode'))
        source_code = cls.normalize_product_code(source_product.get('default_code'))
        source_name = (source_product.get('name') or '').strip()
        
        best_match = {
            'match_type': 'new',
            'matched_product': None,
            'matched_template_id': None,
            'similarity': 0.0,
            'reason': 'Eşleşme bulunamadı'
        }
        
        for target in target_products:
            target_barcode = cls.normalize_barcode(target.get('barcode'))
            target_code = cls.normalize_product_code(target.get('default_code'))
            target_name = (target.get('name') or '').strip()
            target_tmpl_id = target.get('product_tmpl_id')
            if isinstance(target_tmpl_id, (list, tuple)):
                target_tmpl_id = target_tmpl_id[0]
            
            # ADIM 1: Barkod eşleşmesi (kesin eşleşme)
            if source_barcode and target_barcode and source_barcode == target_barcode:
                return {
                    'match_type': 'exact',
                    'matched_product': target,
                    'matched_template_id': target_tmpl_id,
                    'similarity': 1.0,
                    'reason': f'Barkod eşleşti: {source_barcode}'
                }
            
            # ADIM 2: Ürün kodu kontrolü
            if source_code and target_code and source_code == target_code:
                # Ürün kodu aynı + Barkod farklı = VARYANT
                if source_barcode and target_barcode and source_barcode != target_barcode:
                    return {
                        'match_type': 'variant',
                        'matched_product': target,
                        'matched_template_id': target_tmpl_id,
                        'similarity': 1.0,
                        'reason': f'Ürün kodu aynı ({source_code}), barkod farklı → Varyant'
                    }
                # Ürün kodu aynı + Barkod yok veya aynı = Kesin eşleşme
                else:
                    return {
                        'match_type': 'exact',
                        'matched_product': target,
                        'matched_template_id': target_tmpl_id,
                        'similarity': 1.0,
                        'reason': f'Ürün kodu eşleşti: {source_code}'
                    }
            
            # ADIM 3: İsim benzerliği (%50+)
            if source_name and target_name:
                similarity = cls.calculate_similarity(source_name, target_name)
                if similarity >= cls.PRODUCT_NAME_SIMILARITY_THRESHOLD and similarity > best_match['similarity']:
                    best_match = {
                        'match_type': 'similar',
                        'matched_product': target,
                        'matched_template_id': target_tmpl_id,
                        'similarity': similarity,
                        'reason': f'İsim benzerliği: %{int(similarity*100)}'
                    }
        
        return best_match
    
    # ═══════════════════════════════════════════════════════════════
    # CARİ EŞLEŞTİRME PROTOKOLܠ(ŞUBE TESPİTİ DAHİL)
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def match_partner(cls, source_partner, target_partners):
        """
        Cari eşleştirme protokolü (şube tespiti dahil)
        
        Öncelik:
        1. VKN/TCKN eşleşmesi → Kesin eşleşme
        2. Telefon eşleşmesi → Kesin eşleşme
        3. E-posta eşleşmesi → Kesin eşleşme
        4. Cari kodu eşleşmesi → Kesin eşleşme
        5. İsim ≥%80 benzer + Bilgiler farklı → ŞUBE
        6. İsim ≥%50 benzer → Benzer eşleşme
        
        Returns:
            dict: {
                'match_type': 'exact' | 'branch' | 'similar' | 'new',
                'matched_partner': partner or None,
                'parent_id': int or None (şube için ana firma),
                'similarity': float,
                'reason': str,
                'branch_name': str or None
            }
        """
        source_vat = cls.normalize_vat(source_partner.get('vat'))
        source_phone = cls.normalize_phone(source_partner.get('phone') or source_partner.get('mobile'))
        source_mobile = cls.normalize_phone(source_partner.get('mobile'))
        source_email = (source_partner.get('email') or '').lower().strip()
        source_name = (source_partner.get('name') or '').strip()
        source_name_normalized = cls.normalize_company_name(source_name)
        source_ref = (source_partner.get('ref') or '').strip()
        source_address = source_partner.get('street') or source_partner.get('address') or ''
        source_city = source_partner.get('city') or ''
        
        best_match = {
            'match_type': 'new',
            'matched_partner': None,
            'parent_id': None,
            'similarity': 0.0,
            'reason': 'Eşleşme bulunamadı',
            'branch_name': None
        }
        
        branch_candidates = []  # Potansiyel şube eşleşmeleri
        
        for target in target_partners:
            target_vat = cls.normalize_vat(target.get('vat'))
            target_phone = cls.normalize_phone(target.get('phone') or target.get('mobile'))
            target_mobile = cls.normalize_phone(target.get('mobile'))
            target_email = (target.get('email') or '').lower().strip()
            target_name = (target.get('name') or '').strip()
            target_name_normalized = cls.normalize_company_name(target_name)
            target_ref = (target.get('ref') or '').strip()
            target_address = target.get('street') or ''
            target_city = target.get('city') or ''
            target_id = target.get('id')
            
            # ADIM 1: VKN/TCKN eşleşmesi (en güvenilir)
            if source_vat and target_vat and source_vat == target_vat:
                # VKN aynı - aynı şirket veya şubesi
                # Adres/telefon farklı ise şube olabilir
                address_different = (source_address.lower() != target_address.lower()) if source_address and target_address else False
                phone_different = (source_phone != target_phone) if source_phone and target_phone else False
                
                if address_different or phone_different:
                    # Şube adayı olarak işaretle
                    branch_candidates.append({
                        'target': target,
                        'reason': 'VKN aynı, adres/telefon farklı'
                    })
                else:
                    return {
                        'match_type': 'exact',
                        'matched_partner': target,
                        'parent_id': None,
                        'similarity': 1.0,
                        'reason': f'VKN/TCKN eşleşti: {source_vat}',
                        'branch_name': None
                    }
            
            # ADIM 2: Telefon eşleşmesi
            phones_to_check = [p for p in [source_phone, source_mobile] if p]
            target_phones = [p for p in [target_phone, target_mobile] if p]
            for sp in phones_to_check:
                if sp in target_phones:
                    return {
                        'match_type': 'exact',
                        'matched_partner': target,
                        'parent_id': None,
                        'similarity': 1.0,
                        'reason': f'Telefon eşleşti: {sp}',
                        'branch_name': None
                    }
            
            # ADIM 3: E-posta eşleşmesi
            if source_email and target_email and source_email == target_email:
                return {
                    'match_type': 'exact',
                    'matched_partner': target,
                    'parent_id': None,
                    'similarity': 1.0,
                    'reason': f'E-posta eşleşti: {source_email}',
                    'branch_name': None
                }
            
            # ADIM 4: Cari kodu eşleşmesi
            if source_ref and target_ref and source_ref == target_ref:
                return {
                    'match_type': 'exact',
                    'matched_partner': target,
                    'parent_id': None,
                    'similarity': 1.0,
                    'reason': f'Cari kodu eşleşti: {source_ref}',
                    'branch_name': None
                }
            
            # ADIM 5 & 6: İsim benzerliği kontrolü
            if source_name_normalized and target_name_normalized:
                similarity = cls.calculate_similarity(source_name_normalized, target_name_normalized)
                
                # %80+ benzerlik - Şube adayı olabilir
                if similarity >= cls.BRANCH_NAME_SIMILARITY_THRESHOLD:
                    # Adres veya telefon farklı mı?
                    address_different = False
                    if source_address and target_address:
                        addr_sim = cls.calculate_similarity(source_address, target_address)
                        address_different = addr_sim < 0.7
                    
                    phone_different = False
                    if source_phone and target_phone:
                        phone_different = source_phone != target_phone
                    
                    # VKN kontrolü - farklı VKN varsa farklı şirket
                    vat_different = False
                    if source_vat and target_vat:
                        vat_different = source_vat != target_vat
                    
                    if vat_different:
                        # VKN farklı - farklı şirket, şube değil
                        continue
                    
                    if address_different or phone_different:
                        branch_candidates.append({
                            'target': target,
                            'similarity': similarity,
                            'reason': f'İsim %{int(similarity*100)} benzer, bilgiler farklı'
                        })
                    elif similarity > best_match['similarity']:
                        best_match = {
                            'match_type': 'exact',
                            'matched_partner': target,
                            'parent_id': None,
                            'similarity': similarity,
                            'reason': f'İsim benzerliği: %{int(similarity*100)}',
                            'branch_name': None
                        }
                
                # %50-80 arası - Benzer eşleşme
                elif similarity >= cls.PARTNER_NAME_SIMILARITY_THRESHOLD and similarity > best_match['similarity']:
                    best_match = {
                        'match_type': 'similar',
                        'matched_partner': target,
                        'parent_id': None,
                        'similarity': similarity,
                        'reason': f'İsim benzerliği: %{int(similarity*100)}',
                        'branch_name': None
                    }
        
        # Şube adayları varsa değerlendir
        if branch_candidates:
            best_branch = max(branch_candidates, key=lambda x: x.get('similarity', 0.8))
            target = best_branch['target']
            target_id = target.get('id')
            
            # Şube adı oluştur
            branch_name = cls._generate_branch_name(
                source_name,
                source_address,
                source_city,
                target.get('name', '')
            )
            
            return {
                'match_type': 'branch',
                'matched_partner': target,
                'parent_id': target_id,
                'similarity': best_branch.get('similarity', 0.8),
                'reason': best_branch['reason'],
                'branch_name': branch_name
            }
        
        return best_match
    
    @classmethod
    def _generate_branch_name(cls, source_name, source_address, source_city, existing_name):
        """Şube için uygun isim oluştur"""
        base_name = source_name
        
        # Önce şehir/ilçe bulmaya çalış
        location = cls.extract_location_from_address(source_address, source_city)
        
        if location:
            branch_name = f"{base_name} - {location} Şube"
        else:
            # Şehir bulunamadı, numara ver
            branch_name = f"{base_name} - Şube 2"
        
        return branch_name
    
    # ═══════════════════════════════════════════════════════════════
    # FATURA EŞLEŞTİRME PROTOKOLܠ
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def match_invoice(cls, source_invoice, target_invoices, amount_tolerance=1.0):
        """
        Fatura eşleştirme protokolü
        
        Öncelik:
        1. Fatura numarası → Kesin eşleşme
        2. Referans numarası → Kesin eşleşme
        3. Cari + Tarih + Tutar (±tolerans) → Kesin eşleşme
        """
        source_name = (source_invoice.get('name') or '').strip()
        source_ref = (source_invoice.get('ref') or '').strip()
        source_partner_id = source_invoice.get('partner_id')
        source_date = source_invoice.get('invoice_date')
        source_amount = float(source_invoice.get('amount_total') or 0)
        
        if isinstance(source_partner_id, (list, tuple)):
            source_partner_id = source_partner_id[0]
        
        for target in target_invoices:
            target_name = (target.get('name') or '').strip()
            target_ref = (target.get('ref') or '').strip()
            target_partner_id = target.get('partner_id')
            target_date = target.get('invoice_date')
            target_amount = float(target.get('amount_total') or 0)
            
            if isinstance(target_partner_id, (list, tuple)):
                target_partner_id = target_partner_id[0]
            
            # ADIM 1: Fatura numarası eşleşmesi
            if source_name and target_name:
                if source_name == target_name:
                    return {
                        'match_type': 'exact',
                        'matched_invoice': target,
                        'reason': f'Fatura no eşleşti: {source_name}'
                    }
                # Kısmi eşleşme (INV/2025/001 vs 2025/001)
                if source_name in target_name or target_name in source_name:
                    return {
                        'match_type': 'exact',
                        'matched_invoice': target,
                        'reason': f'Fatura no kısmi eşleşti: {source_name}'
                    }
            
            # ADIM 2: Referans eşleşmesi
            if source_ref and target_ref and source_ref == target_ref:
                return {
                    'match_type': 'exact',
                    'matched_invoice': target,
                    'reason': f'Referans eşleşti: {source_ref}'
                }
            
            # ADIM 3: Cari + Tarih + Tutar eşleşmesi
            if (source_partner_id and target_partner_id and
                source_date and target_date and
                str(source_date) == str(target_date) and
                abs(source_amount - target_amount) <= amount_tolerance):
                return {
                    'match_type': 'exact',
                    'matched_invoice': target,
                    'reason': f'Cari+Tarih+Tutar eşleşti'
                }
        
        return {
            'match_type': 'new',
            'matched_invoice': None,
            'reason': 'Eşleşme bulunamadı'
        }
    
    # ═══════════════════════════════════════════════════════════════
    # KATEGORİ EŞLEŞTİRME PROTOKOLܠ
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def match_category(cls, source_category, target_categories):
        """
        Kategori eşleştirme protokolü
        
        Öncelik:
        1. İsim tam eşleşme → Kesin eşleşme
        2. İsim ≥%80 benzer → Benzer eşleşme
        """
        source_name = (source_category.get('name') or '').lower().strip()
        
        for target in target_categories:
            target_name = (target.get('name') or '').lower().strip()
            
            # Tam eşleşme
            if source_name == target_name:
                return {
                    'match_type': 'exact',
                    'matched_category': target,
                    'similarity': 1.0,
                    'reason': f'Kategori adı eşleşti: {source_name}'
                }
        
        # Benzerlik kontrolü
        best_match = None
        best_similarity = 0
        
        for target in target_categories:
            target_name = (target.get('name') or '').lower().strip()
            similarity = cls.calculate_similarity(source_name, target_name)
            
            if similarity >= cls.CATEGORY_SIMILARITY_THRESHOLD and similarity > best_similarity:
                best_match = target
                best_similarity = similarity
        
        if best_match:
            return {
                'match_type': 'similar',
                'matched_category': best_match,
                'similarity': best_similarity,
                'reason': f'Kategori benzerliği: %{int(best_similarity*100)}'
            }
        
        return {
            'match_type': 'new',
            'matched_category': None,
            'similarity': 0,
            'reason': 'Eşleşme bulunamadı'
        }
    
    # ═══════════════════════════════════════════════════════════════
    # SİPARİŞ EŞLEŞTİRME PROTOKOLܠ
    # ═══════════════════════════════════════════════════════════════
    
    @classmethod
    def match_order(cls, source_order, target_orders, amount_tolerance=1.0):
        """
        Sipariş eşleştirme protokolü
        
        Öncelik:
        1. Sipariş numarası → Kesin eşleşme
        2. Müşteri referansı → Kesin eşleşme
        3. Cari + Tarih + Tutar → Kesin eşleşme
        """
        source_name = (source_order.get('name') or '').strip()
        source_ref = (source_order.get('client_order_ref') or '').strip()
        source_partner_id = source_order.get('partner_id')
        source_date = source_order.get('date_order') or source_order.get('create_date')
        source_amount = float(source_order.get('amount_total') or 0)
        
        if isinstance(source_partner_id, (list, tuple)):
            source_partner_id = source_partner_id[0]
        
        for target in target_orders:
            target_name = (target.get('name') or '').strip()
            target_ref = (target.get('client_order_ref') or '').strip()
            
            # Sipariş numarası eşleşmesi
            if source_name and target_name and source_name == target_name:
                return {
                    'match_type': 'exact',
                    'matched_order': target,
                    'reason': f'Sipariş no eşleşti: {source_name}'
                }
            
            # Müşteri referansı eşleşmesi
            if source_ref and target_ref and source_ref == target_ref:
                return {
                    'match_type': 'exact',
                    'matched_order': target,
                    'reason': f'Müşteri ref eşleşti: {source_ref}'
                }
        
        return {
            'match_type': 'new',
            'matched_order': None,
            'reason': 'Eşleşme bulunamadı'
        }


# Modül seviyesinde erişim için
protocols = SyncProtocols()
