# File: 8_uip_duzenleme_ortaklik_payi.py
# -*- coding: utf-8 -*-
"""
PlanX UIP - Duzenleme Ortaklik Payi (DOP) Elite Hesaplama Araci
=================================================================

3194 sayili Imar Kanunu 18. madde kapsaminda DOP analizi:
- Dinamik fonksiyon sutunu secimi
- DOP disi tutulacak deger listesi (kullanici tanimli)
- Opsiyonel etaplama / alt bolge analizi (poligon veya otomatik k-means + Voronoi snap)
- Bes vektor katman + iki tablo + bir interaktif HTML dashboard ciktisi

Etkin Alan = Plan Onama - Sum(DOP disi ozel alanlar)
DOP Alani  = Sum(Yol) + Sum(Kamu donati)
DOP Orani  = DOP Alani / Etkin Alan * 100  (hedef: %45)
"""

import os
import math
import json
import urllib.request
from collections import defaultdict
from datetime import datetime

class _LCG:
    """Deterministic pseudo-random number generator.

    A self-contained 64-bit linear congruential generator (Knuth MMIX constants).
    Not for cryptographic use.
    """
    __slots__ = ("_s",)
    _A = 6364136223846793005
    _C = 1442695040888963407
    _M = (1 << 64) - 1

    def __init__(self, seed: int = 42):
        self._s = (int(seed) * 2 + 0x9E3779B97F4A7C15) & self._M

    def uniform(self, lo: float, hi: float) -> float:
        self._s = (self._A * self._s + self._C) & self._M
        frac = (self._s >> 11) / float(1 << 53)  # top 53 bits -> [0, 1)
        return lo + (hi - lo) * frac

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsWkbTypes,
    QgsFeatureSink,
    QgsProcessingUtils,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from qgis.PyQt.QtCore import QVariant
import processing


# ===================================================================
# REFERANS LISTELER
# ===================================================================

# =================================================================
# MASTER LISTE: dop_values.gpkg'den alinmis 241 uip_fonksiyon kaydi
# (ust_konu_grup, uip_fonksiyon) tuple'lari, ust_konu_grup gore sirali
# Bu liste data/dop_values.gpkg ile senkronize tutulmalidir.
# =================================================================

DOP_MASTER_RECORDS = [
    ('AFET TEHLİKELİ ALANLAR', 'HEYELAN ALANI'),
    ('AFET TEHLİKELİ ALANLAR', 'TAŞKINA MARUZ ALAN'),
    ('AFET TEHLİKELİ ALANLAR', 'YAPI YASAKLI ALAN'),
    ('AFET TEHLİKELİ ALANLAR', 'ÖNLEMLİ ALAN'),
    ('AÇIK VE YEŞİL ALANLAR', 'ARBORETUM - BOTANİK PARKI'),
    ('AÇIK VE YEŞİL ALANLAR', 'AĞAÇLANDIRILACAK ALAN'),
    ('AÇIK VE YEŞİL ALANLAR', 'BAKI VE SEYİR TERASI'),
    ('AÇIK VE YEŞİL ALANLAR', 'FUAR, PANAYIR VE FESTİVAL ALANI'),
    ('AÇIK VE YEŞİL ALANLAR', 'HAYVANAT BAHÇESİ'),
    ('AÇIK VE YEŞİL ALANLAR', 'HİPODROM'),
    ('AÇIK VE YEŞİL ALANLAR', 'KENT ORMANI'),
    ('AÇIK VE YEŞİL ALANLAR', 'KORUNACAK BAHÇE'),
    ('AÇIK VE YEŞİL ALANLAR', 'MESİRE YERİ'),
    ('AÇIK VE YEŞİL ALANLAR', 'MEYDAN'),
    ('AÇIK VE YEŞİL ALANLAR', 'MEZARLIK ALANI'),
    ('AÇIK VE YEŞİL ALANLAR', 'MİLLET BAHÇESİ'),
    ('AÇIK VE YEŞİL ALANLAR', 'PARK'),
    ('AÇIK VE YEŞİL ALANLAR', 'PASİF YEŞİL ALAN'),
    ('AÇIK VE YEŞİL ALANLAR', 'REKREAKTİF ALAN'),
    ('AÇIK VE YEŞİL ALANLAR', 'REKREASYON ALANI'),
    ('AÇIK VE YEŞİL ALANLAR', 'ÇOCUK BAHÇESİ VE OYUN ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'AKDENİZ FOKU YAŞAM ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'DENİZ KAPLUMBAĞALARI ÜREME VE KORUMA ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'DOĞAL KARAKTERİ KORUNACAK ALAN'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'KUMSAL-PLAJ'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'MAKİLİK- FUNDALIK ALAN'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'MERA ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'ORGANİK TARIM ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'ORMAN ALANI'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'TARIMSAL NİTELİKLİ ALAN'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'ZEYTİNLİK ALAN'),
    ('BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', 'ÖRTÜ ALTI TARIM ARAZİSİ'),
    ('DEMİRYOLLARI', 'ANA İSTASYON (GAR)'),
    ('DEMİRYOLLARI', 'ARA İSTASYON'),
    ('DENİZYOLLARI', 'BALIKÇI BARINAĞI'),
    ('DENİZYOLLARI', 'BARINAK'),
    ('DENİZYOLLARI', 'DENİZ İNİŞ RAMPASI'),
    ('DENİZYOLLARI', 'DOLFEN/PLATFORM'),
    ('DENİZYOLLARI', 'GEMİ SÖKÜM YERİ'),
    ('DENİZYOLLARI', 'KIYI KORUMA YAPILARI'),
    ('DENİZYOLLARI', 'KONTEYNER LİMANI'),
    ('DENİZYOLLARI', 'KRUVAZİYER LİMANI'),
    ('DENİZYOLLARI', 'LİMAN'),
    ('DENİZYOLLARI', 'MAHMUZ'),
    ('DENİZYOLLARI', 'MENFEZ'),
    ('DENİZYOLLARI', 'RIHTIM'),
    ('DENİZYOLLARI', 'RO RO LİMANI'),
    ('DENİZYOLLARI', 'TEKNE İMAL VE BAKIM YERİ'),
    ('DENİZYOLLARI', 'TEKNE İMAL VE ÇEKEK YERİ'),
    ('DENİZYOLLARI', 'TERSANE ALANI'),
    ('DENİZYOLLARI', 'YAT LİMANI'),
    ('DENİZYOLLARI', 'İSKELE'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'AKARYAKIT ÜRÜNLERİ DEPOLAMA ALANI '),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'DOĞALGAZ / DAĞITIM TESİSİ ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'ELEKTRONİK HABERLEŞME ALTYAPI ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'ENERJİ DEPOLAMA ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'ENERJİ ÜRETİM ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'NÜKLEER ENERJİ SANTRALİ ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'RAFİNERİ-PETROKİMYA TESİSİ ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'REGÜLATÖR ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'TERMİK SANTRAL ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'TRAFO ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'TÜRBİN ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'YANICI PARLAYICI VE PATLAYICI MADDELER ÜRETİM VE DEPO ALANI'),
    ('ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', 'YENİLENEBİLİR ENERJİ KAYNAKLARINA DAYALI ÜRETİM TESİSİ ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'ANAOKULU ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'HALK EĞİTİM MERKEZİ'),
    ('EĞİTİM TESİSLERİ ALANI', 'LİSE ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'MESLEKİ VE TEKNİK ÖĞRETİM TESİSİ ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'ORTAOKUL ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'YÜKSEK ÖĞRETİM ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'ÖZEL ANAOKULU ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'ÖZEL EĞİTİM ALANI'),
    ('EĞİTİM TESİSLERİ ALANI', 'İLKOKUL ALANI'),
    ('HAVAYOLLARI', 'HAVAALANI/HAVALİMANI'),
    ('HAVAYOLLARI', 'HELİKOPTER İNİŞ ALANI'),
    ('KARAYOLLARI', 'BİSİKLET PARKI'),
    ('KARAYOLLARI', 'ELEKTRİKLİ ARAÇ ŞARJ İSTASYONU'),
    ('KARAYOLLARI', 'GENEL OTOPARK ALANI'),
    ('KARAYOLLARI', 'KATLI OTOPARK'),
    ('KARAYOLLARI', 'TERMİNAL (OTOGAR)'),
    ('KARAYOLLARI', 'TIR, KAMYON, MAKİNE PARKI VE GARAJ ALANI'),
    ('KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', 'HAVARAY İSTASYONU'),
    ('KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', 'HAVAİ HAT İSTASYONU'),
    ('KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', 'RAYLI TOPLU TAŞIMA İSTASYONU'),
    ('KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', 'TOPLU TAŞINIM TÜRLERİ ARASI DEĞİŞİM VE AKTARMA ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'AKARYAKIT VE SERVİS İSTASYONU ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'ASKERİ ALAN'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'BELEDİYE HİZMET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'BETON SANTRALİ'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'DEPOLAMA ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'ENDÜSTRİYEL GELİŞME BÖLGESİ'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'KÜÇÜK SANAYİ ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'LOJİSTİK TESİS ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'PAZAR ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'RESMİ KURUM ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'SANAYİ TESİS ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'SU ÜRÜNLERİ ÜRETİM VE YETİŞTİRME TESİSİ'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'T1 TİCARET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'T2 TİCARET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'T3 TİCARET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TARIM VE HAYVANCILIK TESİS ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TOPLU İŞYERLERİ'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TOPTAN TİCARET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TİCARET - KONUT ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TİCARET - TURİZM ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TİCARET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'TİCARET-TURİZM-KONUT ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'İDARİ HİZMET ALANI'),
    ('KENTSEL ÇALIŞMA ALANLARI', 'İMALATHANE TESİS ALANI'),
    ('KONUT ALANLARI / YERLEŞİM ALANLARI', 'GELİŞME KONUT ALANI'),
    ('KONUT ALANLARI / YERLEŞİM ALANLARI', 'YERLEŞİK KONUT ALANI'),
    ('KORUNACAK ALANLAR', '1. DERECE ARKEOLOJİK SİT ALANI'),
    ('KORUNACAK ALANLAR', '1. DERECE DOĞAL SİT ALANI'),
    ('KORUNACAK ALANLAR', '2. DERECE ARKEOLOJİK SİT ALANI'),
    ('KORUNACAK ALANLAR', '2. DERECE DOĞAL SİT ALANI'),
    ('KORUNACAK ALANLAR', '3. DERECE ARKEOLOJİK SİT ALANI'),
    ('KORUNACAK ALANLAR', '3. DERECE DOĞAL SİT ALANI'),
    ('KORUNACAK ALANLAR', 'EKOLOJİK NİTELİĞİ KORUNACAK ALAN'),
    ('KORUNACAK ALANLAR', 'HASSAS ENDEMİK BİYOTOP ALANI'),
    ('KORUNACAK ALANLAR', 'KENTSEL SİT ALANI'),
    ('KORUNACAK ALANLAR', 'KESİN KORUNACAK HASSAS ALAN'),
    ('KORUNACAK ALANLAR', 'KORUNMASI GEREKLİ FLORA VE FAUNA ALANI'),
    ('KORUNACAK ALANLAR', 'MİLLİ PARK'),
    ('KORUNACAK ALANLAR', 'NİTELİKLİ DOĞAL KORUMA ALANI'),
    ('KORUNACAK ALANLAR', 'SÜRDÜRÜLEBİLİR KORUMA VE KONTROLLÜ KULLANIM ALANI'),
    ('KORUNACAK ALANLAR', 'SİT ETKİLEŞİM GEÇİŞ ALANI SINIRI'),
    ('KORUNACAK ALANLAR', 'TABİAT PARKI ALANI'),
    ('KORUNACAK ALANLAR', 'TABİATI KORUMA ALANI'),
    ('KORUNACAK ALANLAR', 'TARİHİ SİT ALANI'),
    ('KORUNACAK ALANLAR', 'TESCİLLİ ANIT YAPI'),
    ('KORUNACAK ALANLAR', 'TESCİLLİ BİNA'),
    ('KORUNACAK ALANLAR', 'TESCİLLİ PARSEL'),
    ('KORUNACAK ALANLAR', 'TESCİLLİ TABİAT VARLIĞI'),
    ('KORUNACAK ALANLAR', 'ULUSLARARASI SÖZLEŞMELERLE BELİRLENEN KORUMA ALAN SINIRI'),
    ('KORUNACAK ALANLAR', 'YABAN HAYATI KORUMA VE GELİŞTİRME ALANI'),
    ('KORUNACAK ALANLAR', 'YÖRESEL MİMARİ ÖZELLİKLERİ KORUNACAK ALAN'),
    ('KORUNACAK ALANLAR', 'ÖZEL ÇEVRE KORUMA BÖLGESİ (ÖÇK)'),
    ('KORUNACAK ALANLAR', 'ÖÇK BÖLGESİ HASSAS ALAN (A)'),
    ('KORUNACAK ALANLAR', 'ÖÇK BÖLGESİ HASSAS ALAN (B)'),
    ('KORUNACAK ALANLAR', 'ÖÇK BÖLGESİ HASSAS ALAN (C)'),
    ('PLANLAMA SINIRLARI', 'ETAPLAMA SINIRI'),
    ('PLANLAMA SINIRLARI', 'KENTSEL TASARIM PROJESİ SINIRI'),
    ('PLANLAMA SINIRLARI', 'PLAN DEĞİŞİKLİĞİ ONAMA SINIRI'),
    ('PLANLAMA SINIRLARI', 'PLAN ONAMA SINIRI'),
    ('PLANLAMA SINIRLARI', 'YAPI YAKLAŞMA SINIRI'),
    ('PLANLAMA SINIRLARI', 'ÖZEL PROJE ALANI SINIRI '),
    ('PLANLAMA SINIRLARI', 'İMAR HAKKI AKTARIM ALANI SINIRI'),
    ('SAĞLIK TESİSLERİ ALANI', 'AİLE SAĞLIĞI MERKEZİ'),
    ('SAĞLIK TESİSLERİ ALANI', 'HASTANE'),
    ('SAĞLIK TESİSLERİ ALANI', 'SAĞLIK TESİSİ ALANI'),
    ('SAĞLIK TESİSLERİ ALANI', 'ÖZEL SAĞLIK TESİSİ ALANI'),
    ('SOSYAL ALT YAPI ALANLARI', 'SOKAK HAYVANLARI BARINAĞI ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'AÇIK SPOR TESİSİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'KAPALI SPOR TESİSİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'KONGRE VE SERGİ MERKEZİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'KREŞ, GÜNDÜZ BAKIMEVİ'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'KÜLTÜREL TESİS ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'SOSYAL TESİS ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'YAŞLI BAKIMEVİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'YURT ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL AÇIK SPOR TESİSİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL KAPALI SPOR TESİSİ ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL KREŞ, GÜNDÜZ BAKIMEVİ'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL KÜLTÜREL TESİS ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL SOSYAL TESİS ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ÖZEL YURT ALANI'),
    ('SOSYAL VE KÜLTÜREL TESİS ALANI', 'ŞEFKAT EVLERİ ALANI'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'ATIK GERİ KAZANIM TESİSLERİ ALANI'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'ATIKSU TESİSLERİ ALANI (ARITMA, TERFİ MERKEZİ)'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'KATI ATIK TESİSLERİ ALANI (BOŞALTMA, BERTARAF, İŞLEME, TRANSFER VE DEPOLAMA)'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'SU KAYNAKLARI TOPLAMA YERİ (KAPTAJ ALANI)'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'SU YÜZEYİ'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'TEHLİKELİ ATIK TESİSLERİ ALANI (BERTARAF VE DEPOLAMA) '),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'TEKNİK ALTYAPI ALANI'),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'YAPAY ADA '),
    ('SU - ATIKSU VE ATIK SİSTEMLERİ', 'İÇME SUYU TESİSLERİ ALANI (DEPOLAMA, ARITMA, TERFİ MERKEZİ)'),
    ('TURİZM ALANLARI', 'APART OTEL ALANI'),
    ('TURİZM ALANLARI', 'EKOTURİZM/KIRSAL TURİZM'),
    ('TURİZM ALANLARI', 'GOLF ALANI'),
    ('TURİZM ALANLARI', 'GOLF TURİZMİ'),
    ('TURİZM ALANLARI', 'GÜNÜBİRLİK TESİS ALANI'),
    ('TURİZM ALANLARI', 'HOSTEL ALANI'),
    ('TURİZM ALANLARI', 'KAMPİNG ALANI'),
    ('TURİZM ALANLARI', 'KIŞ SPORLARI VE KAYAK TESİSİ ALANI'),
    ('TURİZM ALANLARI', 'MOTEL ALANI'),
    ('TURİZM ALANLARI', 'OTEL ALANI '),
    ('TURİZM ALANLARI', 'PANSİYON ALANI'),
    ('TURİZM ALANLARI', 'SAĞLIK ODAKLI TATİL KÖYÜ'),
    ('TURİZM ALANLARI', 'TATİL KÖYÜ ALANI'),
    ('TURİZM ALANLARI', 'TERMAL TURİZM ALANI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'BORU HATTI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'DEMİRYOLLARI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'ENERJİ NAKİL HATTI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'HAVA ALANI HAVA KORİDORU'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'HAVAALANI/HAVALİMANI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'JEOTERMAL KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'KARAYOLLARI YOL KENARI KORUMA KUŞAĞI '),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'NÜKLEER ENERJİ ÜRETİM ALANI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SAĞLIK KORUMA BANDI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SU KANALLARI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN BÖLGESİ'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN EKOLOJİK ETKİLENME BÖLGESİ'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN MUTLAK KORUMA BÖLGESİ'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN SINIRI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN TAMPON BÖLGESİ'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'SULAK ALAN ÖZEL HÜKÜM BÖLGESİ'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'TÜNEL ETKİ ALANI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'YANICI PARLAYICI VE PATLAYICI MADDELER KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'YER ALTI SU KAYNAKLARI KORUMA ALANLARI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'YER ALTI SU KAYNAKLARI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'İÇME SUYU ANA İLETİM HATTI KORUMA KUŞAĞI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'İÇME VE KULLANMA SUYU KISA MESAFELİ KORUMA ALANI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'İÇME VE KULLANMA SUYU MUTLAK KORUMA ALANI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'İÇME VE KULLANMA SUYU ORTA MESAFELİ KORUMA ALANI'),
    ('YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', 'İÇME VE KULLANMA SUYU UZUN MESAFELİ KORUMA ALANI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'ASKERİ YASAK VE GÜVENLİK BÖLGESİ'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'BOĞAZİÇİ ETKİLENME BÖLGESİ SINIRI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'BOĞAZİÇİ GERİ GÖRÜNÜM BÖLGESİ SINIRI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'BOĞAZİÇİ ÖN GÖRÜNÜM BÖLGESİ SINIRI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'DİĞER ÖZEL KANUNLARLA BELİRLENEN ALAN SINIRLARI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'ENDÜSTRİ BÖLGESİ'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'GECEKONDU ÖNLEME BÖLGESİ SINIRI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'ORGANİZE SANAYİ BÖLGESİ'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'SAHİL ŞERİDİ'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'SERBEST BÖLGE'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'TEKNOLOJİ GELİŞTİRME BÖLGESİ'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'TOPLU KONUT ALANI SINIRI'),
    ('ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', 'TURİZM MERKEZİ/KÜLTÜR VE TURİZM KORUMA VE GELİŞİM ALT BÖLGE SINIRI'),
    ('İBADET ALANLARI', 'CAMİ'),
    ('İBADET ALANLARI', 'KİLİSE'),
    ('İBADET ALANLARI', 'MESCİT'),
    ('İBADET ALANLARI', 'SİNAGOG (HAVRA)'),
    ('İBADET ALANLARI', 'ŞAPEL'),
    ('İDARİ SINIRLAR', 'BELEDİYE SINIRI'),
    ('İDARİ SINIRLAR', 'KÖY SINIRI'),
    ('İDARİ SINIRLAR', 'MAHALLE SINIRI'),
    ('İDARİ SINIRLAR', 'MÜCAVİR ALAN SINIRI'),
    ('İDARİ SINIRLAR', 'ÜLKE SINIRI'),
    ('İDARİ SINIRLAR', 'İL SINIRI'),
    ('İDARİ SINIRLAR', 'İLÇE SINIRI'),
]

# Master listenin uip_fonksiyon ve ust_konu_grup ayri sirali listeleri
MASTER_FONK_LIST = [t[1].strip() for t in DOP_MASTER_RECORDS]  # 241 element
MASTER_USTGRUP_MAP = {t[1].strip().upper(): t[0] for t in DOP_MASTER_RECORDS}

# Etiket: gosterimde "[GRUP] FONKSIYON" biciminde
MASTER_LABELS = ["[%s] %s" % (t[0], t[1].strip()) for t in DOP_MASTER_RECORDS]

# Ust grup -> indeksler eslemesi (toplu secim icin kullanilabilir)
def _idx_by_groups(group_names):
    s = set(g.upper() for g in group_names)
    return [i for i, t in enumerate(DOP_MASTER_RECORDS) if t[0].upper() in s]

def _idx_by_prefix(prefix_or_contains):
    """Belirli kelime icerigi olan uip_fonksiyon'larin index'lerini dondurur"""
    out = []
    for i, t in enumerate(DOP_MASTER_RECORDS):
        f = t[1].strip().upper()
        if any(p in f for p in prefix_or_contains):
            out.append(i)
    return out

# DEFAULT DEGER ATAMALARI (akilli onseki)

# HARIC: planlama sinirlari, idari sinirlar, yapi sinirlamasi koruma kusaklari,
# afet alanlari, korunacak alanlar, ozel kanunlarla belirlenen alan ve sinirlar,
# bugunku arazi kullanimi (tarim/orman/zeytinlik korunacak), denizyollari (deniz uzeri)
DEFAULT_HARIC_GROUPS = [
    'PLANLAMA SINIRLARI',
    'İDARİ SINIRLAR',
    'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR',
    'AFET TEHLİKELİ ALANLAR',
    'KORUNACAK ALANLAR',
    'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR',
    'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR',
]
DEFAULT_HARIC_IDX = _idx_by_groups(DEFAULT_HARIC_GROUPS)

# OZEL: konut, ticaret, turizm, sanayi/calisma, "OZEL ..." prefix'li tum kullanimlar
DEFAULT_OZEL_GROUPS = [
    'KONUT ALANLARI / YERLEŞİM ALANLARI',
    'TURİZM ALANLARI',
]
DEFAULT_OZEL_FROM_GROUPS = _idx_by_groups(DEFAULT_OZEL_GROUPS)

# KENTSEL CALISMA ALANLARI grubundan: ticaret/sanayi/depolama/lojistik OZEL,
# ama BELEDIYE HIZMET ALANI, RESMI KURUM ALANI, IDARI HIZMET ALANI, PAZAR KAMU
KENTSEL_CALISMA_OZEL_FONKLAR = {
    'AKARYAKIT VE SERVİS İSTASYONU ALANI',
    'BETON SANTRALİ', 'DEPOLAMA ALANI',
    'ENDÜSTRİYEL GELİŞME BÖLGESİ', 'KÜÇÜK SANAYİ ALANI',
    'LOJİSTİK TESİS ALANI', 'SANAYİ TESİS ALANI',
    'SU ÜRÜNLERİ ÜRETİM VE YETİŞTİRME TESİSİ',
    'T1 TİCARET ALANI', 'T2 TİCARET ALANI', 'T3 TİCARET ALANI',
    'TARIM VE HAYVANCILIK TESİS ALANI', 'TOPLU İŞYERLERİ',
    'TOPTAN TİCARET ALANI', 'TİCARET - KONUT ALANI',
    'TİCARET - TURİZM ALANI', 'TİCARET ALANI', 'TİCARET-TURİZM-KONUT ALANI',
    'İMALATHANE TESİS ALANI',
    'ASKERİ ALAN',  # askeri alan ozel
}
DEFAULT_OZEL_FROM_KENTSEL = [
    i for i, t in enumerate(DOP_MASTER_RECORDS)
    if t[0] == 'KENTSEL ÇALIŞMA ALANLARI' and t[1].strip().upper() in
       {x.upper() for x in KENTSEL_CALISMA_OZEL_FONKLAR}
]

# "OZEL ..." prefix'li olanlar (ozel saglik, ozel egitim, ozel kres, vs.)
DEFAULT_OZEL_FROM_OZELS = [
    i for i, t in enumerate(DOP_MASTER_RECORDS)
    if t[1].strip().upper().startswith('ÖZEL ')
]

DEFAULT_OZEL_IDX = sorted(set(DEFAULT_OZEL_FROM_GROUPS + DEFAULT_OZEL_FROM_KENTSEL + DEFAULT_OZEL_FROM_OZELS))

# KAMU: aciksaha+yesil, egitim (ozel haric), saglik (ozel haric), ibadet,
# sosyal/kulturel (ozel haric), karayollari, demiryollari, havayollari, denizyollari,
# kentsel toplu tasima, enerji, su-atiksu, sosyal alt yapi,
# kentsel calisma alanlarindan: belediye/resmi/idari/pazar
KAMU_GROUPS_FULL = [
    'AÇIK VE YEŞİL ALANLAR',
    'İBADET ALANLARI',
    'KARAYOLLARI',
    'DEMİRYOLLARI', 'DENİZYOLLARI', 'HAVAYOLLARI',
    'KENTSEL TOPLU TAŞIMA GÜZERGAHLARI',
    'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA',
    'SU - ATIKSU VE ATIK SİSTEMLERİ',
    'SOSYAL ALT YAPI ALANLARI',
]
DEFAULT_KAMU_IDX = _idx_by_groups(KAMU_GROUPS_FULL)
# Egitim, saglik, sosyal/kulturelden ozel olmayanlari ekle
for i, t in enumerate(DOP_MASTER_RECORDS):
    g, f = t[0], t[1].strip().upper()
    if g in ('EĞİTİM TESİSLERİ ALANI', 'SAĞLIK TESİSLERİ ALANI',
             'SOSYAL VE KÜLTÜREL TESİS ALANI') and not f.startswith('ÖZEL '):
        if i not in DEFAULT_KAMU_IDX:
            DEFAULT_KAMU_IDX.append(i)
# Kentsel calismadan kamu olanlar
KENTSEL_KAMU_FONKLAR = {'BELEDİYE HİZMET ALANI', 'RESMİ KURUM ALANI',
                         'İDARİ HİZMET ALANI', 'PAZAR ALANI'}
for i, t in enumerate(DOP_MASTER_RECORDS):
    if t[0] == 'KENTSEL ÇALIŞMA ALANLARI' and t[1].strip().upper() in KENTSEL_KAMU_FONKLAR:
        if i not in DEFAULT_KAMU_IDX:
            DEFAULT_KAMU_IDX.append(i)
DEFAULT_KAMU_IDX = sorted(DEFAULT_KAMU_IDX)

# ACIK-YESIL (9. madde): park, cocuk bahcesi, meydan, semt spor alani,
# botanik parki, mesire yeri, rekreasyon
ACIK_YESIL_FONKLAR = {
    'PARK', 'ÇOCUK BAHÇESİ VE OYUN ALANI', 'MEYDAN',
    'AÇIK SPOR TESİSİ ALANI',
    'REKREASYON ALANI', 'REKREAKTİF ALAN',
    'MESİRE YERİ', 'ARBORETUM - BOTANİK PARKI',
    'MİLLET BAHÇESİ',
}
DEFAULT_AY_IDX = [
    i for i, t in enumerate(DOP_MASTER_RECORDS)
    if t[1].strip().upper() in {x.upper() for x in ACIK_YESIL_FONKLAR}
]

# Geri uyumluluk
DEFAULT_OZEL_FONKSIYONLAR = [DOP_MASTER_RECORDS[i][1].strip() for i in DEFAULT_OZEL_IDX]
DEFAULT_KAMU_DONATI_FONKSIYONLAR = [DOP_MASTER_RECORDS[i][1].strip() for i in DEFAULT_KAMU_IDX]
DEFAULT_ACIK_YESIL_FONKSIYONLAR = [DOP_MASTER_RECORDS[i][1].strip() for i in DEFAULT_AY_IDX]
DEFAULT_DOP_DISI_FONKSIYONLAR = DEFAULT_OZEL_FONKSIYONLAR
ACIK_YESIL_FONKSIYONLAR = DEFAULT_ACIK_YESIL_FONKSIYONLAR

ASSETS_DIR_NAME = "assets"
PLOTLY_FILENAME = "plotly-2.27.0.min.js"
LEAFLET_JS_FILENAME = "leaflet-1.9.4.min.js"
LEAFLET_CSS_FILENAME = "leaflet-1.9.4.min.css"

PLOTLY_URL = "https://cdn.plot.ly/plotly-2.27.0.min.js"
LEAFLET_JS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
LEAFLET_CSS_URL = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"


# ===================================================================
# YARDIMCI: ALAN-AGIRLIKLI K-MEANS (saf python, numpy gerektirmez)
# ===================================================================

def _d2(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def area_weighted_kmeans(points, weights, k, max_iter=80, seed=42):
    """Alan-agirlikli k-means. Buyuk adalar k-means++ seed'inde oncelikli.
       Kapasite cezasi ile alan dengesi saglanir."""
    n = len(points)
    if n == 0:
        return [], []
    if k <= 1:
        sx = sum(points[i][0] * weights[i] for i in range(n))
        sy = sum(points[i][1] * weights[i] for i in range(n))
        sw = sum(weights) or 1.0
        return [0] * n, [(sx / sw, sy / sw)]
    if k >= n:
        return list(range(n)), list(points)

    rng = _LCG(seed)

    # K-means++ seeding (weighted)
    first_idx = max(range(n), key=lambda i: weights[i])
    centers = [points[first_idx]]
    chosen = {first_idx}
    for _ in range(k - 1):
        distances = []
        for i in range(n):
            min_d2 = min(_d2(points[i], c) for c in centers)
            distances.append(min_d2 * weights[i])
        total = sum(distances)
        if total <= 0:
            remaining = [i for i in range(n) if i not in chosen]
            next_idx = remaining[0] if remaining else 0
        else:
            r = rng.uniform(0, total)
            cumulative = 0.0
            next_idx = n - 1
            for i, d in enumerate(distances):
                cumulative += d
                if cumulative >= r:
                    next_idx = i
                    break
        centers.append(points[next_idx])
        chosen.add(next_idx)

    target_w = sum(weights) / k
    labels = [0] * n

    for _ in range(max_iter):
        cluster_w = [0.0] * k
        new_labels = [-1] * n
        order = sorted(range(n), key=lambda i: -weights[i])
        for i in order:
            best, best_d = 0, float('inf')
            for ci, c in enumerate(centers):
                d = _d2(points[i], c)
                penalty = 1.0
                if cluster_w[ci] >= target_w * 0.95:
                    excess = (cluster_w[ci] / target_w) if target_w > 0 else 1.0
                    penalty = 1.0 + 0.6 * (excess ** 1.5)
                d_pen = d * penalty
                if d_pen < best_d:
                    best_d, best = d_pen, ci
            new_labels[i] = best
            cluster_w[best] += weights[i]

        new_centers = []
        for ci in range(k):
            sx, sy, sw = 0.0, 0.0, 0.0
            for i in range(n):
                if new_labels[i] == ci:
                    sx += points[i][0] * weights[i]
                    sy += points[i][1] * weights[i]
                    sw += weights[i]
            if sw > 0:
                new_centers.append((sx / sw, sy / sw))
            else:
                largest_ci = max(range(k), key=lambda x: cluster_w[x])
                farthest = max(
                    (i for i in range(n) if new_labels[i] == largest_ci),
                    key=lambda i: _d2(points[i], centers[largest_ci]),
                    default=0
                )
                new_centers.append(points[farthest])

        shift = sum(math.sqrt(_d2(centers[i], new_centers[i])) for i in range(k))
        centers = new_centers
        labels = new_labels
        if shift < 1.0:
            break

    return labels, centers


# ===================================================================
# YARDIMCI: ASSET INDIRME / EMBED
# ===================================================================

def _assets_dir(plugin_dir):
    d = os.path.join(plugin_dir, ASSETS_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def _ensure_asset(assets_dir, filename, url, feedback):
    """
    Plotly / Leaflet asset'ini ilk kullanimda https CDN'den indirip yerel
    cache'e yazar. Sonraki cagrilarda dosya varsa atlanir.

    Guvenlik: URL'in https sema kontrolu yapilir (file://, ftp://, custom
    schemes engellenir). URL sabit liste icindedir (modul ust kisminda
    tanimlandi); kullanici girdisi degildir. urlopen cagrisi Bandit B310
    icin # nosec ile isaretlidir cunku sema dogrulanmistir.
    """
    fp = os.path.join(assets_dir, filename)
    if os.path.exists(fp) and os.path.getsize(fp) > 2000:
        return fp
    # Sadece https semasini kabul et
    if not isinstance(url, str) or not url.lower().startswith('https://'):
        feedback.pushInfo("UYARI: Yalnizca https URL kabul edilir, atlandi: " + str(url))
        return None
    try:
        feedback.pushInfo("Asset indiriliyor: " + url)
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 PlanX-QGIS"})
        # https sema yukarida dogrulandi; B310 buradaki dinamik sema riskini ariyor.
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            data = resp.read()
        with open(fp, "wb") as f:
            f.write(data)
        feedback.pushInfo("Asset kaydedildi: %s (%d KB)" % (filename, len(data) // 1024))
        return fp
    except Exception as e:
        feedback.pushInfo("UYARI: Asset indirilemedi (%s): %s" % (filename, e))
        return None


def _load_asset(assets_dir, filename):
    fp = os.path.join(assets_dir, filename)
    if not os.path.exists(fp):
        return None
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(fp, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception:
            return None


# ===================================================================
# ANA ALGORITMA
# ===================================================================

class DuzenlemeOrtaklikPayiUIP(QgsProcessingAlgorithm):

    PLAN_SINIR = 'plan_onama_siniri'
    PLAN_LAYER = 'plan_katmani'
    FONK_FIELD = 'fonksiyon_sutunu'

    # YENI TASARIM: master listeden 4 tiklenebilir enum
    HARIC_ENUM = 'haric_fonksiyonlar_secim'      # DOP hesabindan TAMAMEN haric (sit, koruma, sinir vb.)
    HARIC_EKSTRA = 'haric_fonksiyonlar_ekstra'
    OZEL_ENUM = 'ozel_fonksiyonlar_secim'        # DOP hesabina dahil ama DOP'a (paya) girmez
    OZEL_EKSTRA = 'ozel_fonksiyonlar_ekstra'
    KAMU_ENUM = 'kamu_donati_secim'              # DOP'a (paya) girer
    KAMU_EKSTRA = 'kamu_donati_ekstra'
    AY_ENUM = 'acik_yesil_secim'                 # 9. madde %75 alt kumesi (KAMU icinden)
    AY_EKSTRA = 'acik_yesil_ekstra'

    DIGER_VARSAYIM = 'diger_varsayim'           # 0=KAMU, 1=OZEL, 2=HARIC

    PLAN_NUFUS = 'plan_nufusu'
    ETAP_LAYER = 'etap_katmani'
    ETAP_SAYI = 'etap_sayisi'
    IDEAL_DOP = 'ideal_dop_orani'
    HTML_MODE = 'html_embed_mode'

    OUT_DOP_ESAS = 'OUT_DOP_ESAS'
    OUT_DOP_DISI = 'OUT_DOP_DISI'
    OUT_YOL_KAMU = 'OUT_YOL_KAMU'
    OUT_ETAP = 'OUT_ETAP'
    OUT_TABLO_FONK = 'OUT_TABLO_FONK'
    OUT_TABLO_OZET = 'OUT_TABLO_OZET'
    OUT_HTML = 'OUT_HTML'

    def initAlgorithm(self, config=None):
        p = QgsProcessingParameterVectorLayer(
            self.PLAN_SINIR, 'Plan Onama Sınırı (Poligon)',
            [QgsProcessing.TypeVectorPolygon])
        p.setHelp('DOP hesabının yapılacağı plan onama sınırı (tek veya çoklu poligon).')
        self.addParameter(p)

        p = QgsProcessingParameterVectorLayer(
            self.PLAN_LAYER, 'UİP Plan Katmanı (Fonksiyon Adaları)',
            [QgsProcessing.TypeVectorPolygon])
        p.setHelp('Her ada/parselin fonksiyonunu taşıyan poligon katman.')
        self.addParameter(p)

        p = QgsProcessingParameterField(
            self.FONK_FIELD, 'Fonksiyon Sütunu (örn. uipfonksiyon)',
            parentLayerParameterName=self.PLAN_LAYER,
            type=QgsProcessingParameterField.String,
            defaultValue='uipfonksiyon')
        p.setHelp('Adaların fonksiyon adını tutan sütun. Dinamik olarak plan katmanından seçilir.')
        self.addParameter(p)

        # -------- 1. HARIC (DOP hesabindan TAMAMEN cikar) --------
        p = QgsProcessingParameterEnum(
            self.HARIC_ENUM,
            'DOP HESABINDAN TAMAMEN HARİÇ — TİKLEYEREK seçin (sit, koruma kuşağı, sınır şeridi vb.)',
            options=MASTER_LABELS,
            allowMultiple=True,
            defaultValue=DEFAULT_HARIC_IDX)
        p.setHelp('Bu fonksiyondaki adalar DOP hesabının HEM payından HEM paydasından çıkarılır. '
                  'Plan onama sınırı, sit sınırları, Boğaziçi koruma bantları, askeri yasak bölge, '
                  'idari sınırlar gibi düzenleme alanı olmayan kullanımlar bu listede olmalıdır. '
                  'Default: Planlama Sınırları, İdari Sınırlar, Korunacak Alanlar, '
                  'Yapı Sınırlaması Koruma Kuşakları, Afet Tehlikeli Alanlar, Özel Kanunlar '
                  've Bugünkü Arazi Kullanımı korunacak grupları tikli gelir.')
        self.addParameter(p)

        p = QgsProcessingParameterString(
            self.HARIC_EKSTRA,
            'EK Hariç Değerleri (master listede yoksa her satıra bir değer)',
            defaultValue='', multiLine=True, optional=True)
        self.addParameter(p)

        # -------- 2. OZEL (DOP'a dahil ama paya girmez) --------
        p = QgsProcessingParameterEnum(
            self.OZEL_ENUM,
            'ÖZEL Fonksiyonlar (mülkiyet arsa sahibinde) — TİKLEYEREK seçin (konut, ticaret, turizm, sanayi vb.)',
            options=MASTER_LABELS,
            allowMultiple=True,
            defaultValue=DEFAULT_OZEL_IDX)
        p.setHelp('Bu fonksiyondaki adalar arsa sahibinin mülkiyetinde kalır. '
                  'DOP hesabı PAYDA\'sına dahildir (etkin alana sayılır) ama PAY\'a girmez. '
                  'Default: Konut, Turizm grupları + Kentsel Çalışmadaki ticaret/sanayi + '
                  '"ÖZEL ..." prefix\'li özel sağlık/eğitim/sosyal/spor kullanımları.')
        self.addParameter(p)

        p = QgsProcessingParameterString(
            self.OZEL_EKSTRA,
            'EK Özel Değerleri (her satıra bir değer)',
            defaultValue='', multiLine=True, optional=True)
        self.addParameter(p)

        # -------- 3. KAMU DONATI (DOP'a giren — paya dahil) --------
        p = QgsProcessingParameterEnum(
            self.KAMU_ENUM,
            'KAMU DONATI Fonksiyonları (DOP\'a giren) — TİKLEYEREK seçin (park, okul, hastane, ibadet vb.)',
            options=MASTER_LABELS,
            allowMultiple=True,
            defaultValue=DEFAULT_KAMU_IDX)
        p.setHelp('Bu fonksiyondaki adalar kamuya geçer; DOP hesabının PAY\'ına ve PAYDA\'sına dahildir. '
                  'Default: Açık-Yeşil, Eğitim/Sağlık/Sosyal (özel olmayan), İbadet, ulaşım, '
                  'enerji, su-atıksu altyapı, kentsel çalışmadan belediye/resmi/idari/pazar.')
        self.addParameter(p)

        p = QgsProcessingParameterString(
            self.KAMU_EKSTRA,
            'EK Kamu Donatı Değerleri (her satıra bir değer)',
            defaultValue='', multiLine=True, optional=True)
        self.addParameter(p)

        # -------- 4. ACIK-YESIL (9. madde %75 alt kumesi) --------
        p = QgsProcessingParameterEnum(
            self.AY_ENUM,
            'AÇIK-YEŞİL ALT KÜMESİ (9. madde %75 kontrolü için) — TİKLEYEREK seçin',
            options=MASTER_LABELS,
            allowMultiple=True,
            defaultValue=DEFAULT_AY_IDX)
        p.setHelp('9. madde gereği DOP içindeki açık-yeşil (park, çocuk bahçesi, meydan, semt spor '
                  'alanı, mesire yeri, rekreasyon) toplam oranı %75 üstünde olmalıdır.')
        self.addParameter(p)

        p = QgsProcessingParameterString(
            self.AY_EKSTRA,
            'EK Açık-Yeşil Değerleri (her satıra bir değer)',
            defaultValue='', multiLine=True, optional=True)
        self.addParameter(p)

        # -------- 5. KATEGORIZE EDILMEMIS ADA VARSAYIMI --------
        p = QgsProcessingParameterEnum(
            self.DIGER_VARSAYIM,
            'Hiçbir kategoride olmayan (TANIMSIZ) adalar varsayılan olarak nasıl sayılsın?',
            options=['KAMU gibi say (DOP\'a dahil — pay+payda)',
                     'ÖZEL gibi say (sadece payda, paya değil)',
                     'HARİÇ gibi say (hem pay hem payda dışı)'],
            allowMultiple=False, defaultValue=0)
        p.setHelp('Master listede HARIÇ/ÖZEL/KAMU/AÇIK-YEŞİL hiçbirinde tikli olmayan adalar '
                  'için varsayım. Uyarı log\'larda gösterilir. En güvenli: KAMU say (default).')
        self.addParameter(p)

        # -------- DİĞER --------
        p = QgsProcessingParameterNumber(
            self.PLAN_NUFUS, 'Plan Nüfusu (kişi)',
            QgsProcessingParameterNumber.Double,
            defaultValue=10000.0, minValue=1.0)
        self.addParameter(p)

        p = QgsProcessingParameterVectorLayer(
            self.ETAP_LAYER,
            'Etaplama / DOP Alt Bölge Katmanı (Poligon, OPSİYONEL)',
            [QgsProcessing.TypeVectorPolygon], optional=True)
        p.setHelp('Alt bölge analizi için poligon katman. Verilmezse aşağıdaki sayıya göre '
                  'otomatik etaplama (alan-ağırlıklı k-means + ada-snap) uygulanır.')
        self.addParameter(p)

        p = QgsProcessingParameterNumber(
            self.ETAP_SAYI,
            'Otomatik Etaplama Sayısı (etap katmanı verilmezse, 1=tek bölge)',
            QgsProcessingParameterNumber.Integer,
            defaultValue=4, minValue=1, maxValue=20)
        p.setHelp('Otomatik bölmede oluşturulacak alt bölge sayısı. Sınırlar adaların '
                  'arasından geçer; hiçbir ada kesilmez.')
        self.addParameter(p)

        p = QgsProcessingParameterNumber(
            self.IDEAL_DOP, 'İdeal DOP Oranı (%)',
            QgsProcessingParameterNumber.Double,
            defaultValue=45.0, minValue=10.0, maxValue=80.0)
        p.setHelp('Hedef DOP oranı (default %45 - yönetmelik tavsiyesi).')
        self.addParameter(p)

        p = QgsProcessingParameterEnum(
            self.HTML_MODE,
            'HTML Rapor Modu (Plotly + Leaflet)',
            options=['CDN (online — küçük dosya, hızlı)',
                     'INLINE (offline — büyük dosya, internet gerekmez)'],
            allowMultiple=False, defaultValue=0)
        p.setHelp('CDN: Plotly + Leaflet kütüphaneleri internetten yüklenir (HTML ~50 KB). '
                  'INLINE: Kütüphaneler HTML\'in içine gömülür (~3.5 MB, ilk kullanımda indirilir).')
        self.addParameter(p)

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_DOP_ESAS, 'Çıktı 1: DOP Esas Alanlar (Poligon)',
            type=QgsProcessing.TypeVectorPolygon))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_DOP_DISI, 'Çıktı 2: DOP Dışı Özel Alanlar (Poligon)',
            type=QgsProcessing.TypeVectorPolygon))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_YOL_KAMU, 'Çıktı 3: Yol ve Kamu Alanları (Poligon)',
            type=QgsProcessing.TypeVectorPolygon))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_ETAP, 'Çıktı 4: Etaplama Alt Bölgeleri (Poligon)',
            type=QgsProcessing.TypeVectorPolygon))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_TABLO_FONK, 'Çıktı 5: Fonksiyon × Etap Tablosu',
            type=QgsProcessing.TypeVector))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUT_TABLO_OZET, 'Çıktı 6: DOP Oran Özet Tablosu (Global + Etap)',
            type=QgsProcessing.TypeVector))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUT_HTML, 'Çıktı 7: HTML Dashboard Rapor',
            fileFilter='HTML files (*.html)'))

    # =========================================================
    # ANA PROCESS
    # =========================================================

    def processAlgorithm(self, parameters, context, feedback):
        sinir_layer = self.parameterAsVectorLayer(parameters, self.PLAN_SINIR, context)
        plan_layer = self.parameterAsVectorLayer(parameters, self.PLAN_LAYER, context)
        fonk_field = self.parameterAsString(parameters, self.FONK_FIELD, context)

        haric_idx = self.parameterAsEnums(parameters, self.HARIC_ENUM, context)
        haric_extra = self.parameterAsString(parameters, self.HARIC_EKSTRA, context)
        ozel_idx = self.parameterAsEnums(parameters, self.OZEL_ENUM, context)
        ozel_extra = self.parameterAsString(parameters, self.OZEL_EKSTRA, context)
        kamu_idx = self.parameterAsEnums(parameters, self.KAMU_ENUM, context)
        kamu_extra = self.parameterAsString(parameters, self.KAMU_EKSTRA, context)
        ay_idx = self.parameterAsEnums(parameters, self.AY_ENUM, context)
        ay_extra = self.parameterAsString(parameters, self.AY_EKSTRA, context)

        diger_varsayim = self.parameterAsEnum(parameters, self.DIGER_VARSAYIM, context)
        # 0=KAMU, 1=OZEL, 2=HARIC
        diger_kategori = ['KAMU', 'OZEL', 'HARIC'][diger_varsayim]

        nufus = self.parameterAsDouble(parameters, self.PLAN_NUFUS, context)
        etap_layer = self.parameterAsVectorLayer(parameters, self.ETAP_LAYER, context)
        etap_sayi = self.parameterAsInt(parameters, self.ETAP_SAYI, context)
        ideal_dop = self.parameterAsDouble(parameters, self.IDEAL_DOP, context)
        html_mode = self.parameterAsEnum(parameters, self.HTML_MODE, context)
        html_path = self.parameterAsFileOutput(parameters, self.OUT_HTML, context)

        def _build_set_from_master(enum_idx, extra_str):
            """Master listenin index'lerinden uip_fonksiyon string set'i olustur."""
            s = set()
            for i in enum_idx or []:
                if 0 <= i < len(DOP_MASTER_RECORDS):
                    s.add(DOP_MASTER_RECORDS[i][1].strip().upper())
            for line in (extra_str or "").splitlines():
                v = line.strip().upper()
                if v:
                    s.add(v)
            return s

        haric_set = _build_set_from_master(haric_idx, haric_extra)
        ozel_set = _build_set_from_master(ozel_idx, ozel_extra)
        kamu_set = _build_set_from_master(kamu_idx, kamu_extra)
        ay_set = _build_set_from_master(ay_idx, ay_extra)

        # Oncelik: HARIC > OZEL > KAMU. Cakismalari sirayla cikar.
        ozel_set = ozel_set - haric_set
        kamu_set = kamu_set - haric_set - ozel_set

        feedback.pushInfo("Kategori: %d haric | %d ozel | %d kamu donati | %d acik-yesil tanimli." %
                          (len(haric_set), len(ozel_set), len(kamu_set), len(ay_set)))
        feedback.pushInfo("Tanimsiz fonksiyonlar varsayilan kategori: %s" % diger_kategori)

        plan_geoms = [f.geometry() for f in sinir_layer.getFeatures() if f.geometry() and not f.geometry().isEmpty()]
        if not plan_geoms:
            raise QgsProcessingException("Plan onama siniri katmani bos.")
        plan_geom = QgsGeometry.unaryUnion(plan_geoms)
        plan_alan = plan_geom.area()
        feedback.pushInfo("Plan onama alani: %.2f m2" % plan_alan)

        feedback.pushInfo("Plan katmani onama sinirina kesiliyor...")
        clipped_res = processing.run(
            'native:clip',
            {'INPUT': parameters[self.PLAN_LAYER],
             'OVERLAY': parameters[self.PLAN_SINIR],
             'OUTPUT': 'memory:'},
            context=context, feedback=feedback, is_child_algorithm=True)
        clipped_layer = QgsProcessingUtils.mapLayerFromString(clipped_res['OUTPUT'], context)

        clipped_field_names = [fl.name() for fl in clipped_layer.fields()]
        if fonk_field not in clipped_field_names:
            raise QgsProcessingException(
                "Secilen fonksiyon sutunu '%s' kesilmis katmanda bulunamadi." % fonk_field)

        adalar = []
        ada_id = 0
        diger_fonk_sayim = defaultdict(int)
        for f in clipped_layer.getFeatures():
            geom = f.geometry()
            if not geom or geom.isEmpty():
                continue
            fonk_raw = f[fonk_field]
            fonk = str(fonk_raw).strip().upper() if fonk_raw is not None else ""
            alan = geom.area()
            if alan <= 0:
                continue
            # Kategori belirle: HARIC > OZEL > KAMU > DIGER (kullanici varsayimina dustu)
            if fonk in haric_set:
                kategori = 'HARIC'
            elif fonk in ozel_set:
                kategori = 'OZEL'
            elif fonk in kamu_set:
                kategori = 'KAMU'
            else:
                kategori = diger_kategori   # Kullanicinin secimi: KAMU / OZEL / HARIC
                diger_fonk_sayim[fonk] += 1
            adalar.append({
                'id': ada_id, 'geom': QgsGeometry(geom), 'fonk': fonk,
                'alan': alan, 'kategori': kategori,
                'is_haric': kategori == 'HARIC',
                'is_disi': kategori in ('OZEL', 'HARIC'),
                'is_kamu': kategori == 'KAMU',
                'is_ay': fonk in ay_set and kategori == 'KAMU',
                'is_tanimsiz': fonk not in haric_set and fonk not in ozel_set and fonk not in kamu_set,
            })
            ada_id += 1

        if diger_fonk_sayim:
            feedback.pushInfo("UYARI: %d adet TANIMSIZ fonksiyon kategori secilmemis (varsayim: %s):" %
                              (sum(diger_fonk_sayim.values()), diger_kategori))
            for fk, ct in sorted(diger_fonk_sayim.items(), key=lambda x: -x[1])[:15]:
                feedback.pushInfo("  - %s (%d ada)" % (fk or '<bos>', ct))

        haric_alan_total = sum(a['alan'] for a in adalar if a['kategori'] == 'HARIC')
        ozel_alan_total = sum(a['alan'] for a in adalar if a['kategori'] == 'OZEL')
        kamu_alan_total = sum(a['alan'] for a in adalar if a['kategori'] == 'KAMU')
        feedback.pushInfo("Toplam %d ada | HARIC: %d (%.0f m2) | OZEL: %d (%.0f m2) | KAMU: %d (%.0f m2)" %
                          (len(adalar),
                           sum(1 for a in adalar if a['kategori'] == 'HARIC'), haric_alan_total,
                           sum(1 for a in adalar if a['kategori'] == 'OZEL'), ozel_alan_total,
                           sum(1 for a in adalar if a['kategori'] == 'KAMU'), kamu_alan_total))

        if etap_layer is not None:
            etap_bolgeleri = self._etap_from_layer(etap_layer, plan_geom, feedback)
            etap_kaynak = 'KULLANICI'
        else:
            etap_bolgeleri = self._etap_otomatik(adalar, plan_geom, etap_sayi, feedback)
            etap_kaynak = 'OTOMATIK'
        if not etap_bolgeleri:
            etap_bolgeleri = {0: plan_geom}
        feedback.pushInfo("Etaplama (%s): %d alt bolge." % (etap_kaynak, len(etap_bolgeleri)))

        ada_etap_id = self._adalari_etaplara_ata(adalar, etap_bolgeleri)

        global_metric = self._hesapla_metrik(adalar, plan_alan, ideal_dop)
        global_metric['nufus'] = nufus
        global_metric['ada_sayisi'] = len(adalar)
        global_metric['haric_ada_sayisi'] = sum(1 for a in adalar if a['kategori'] == 'HARIC')
        global_metric['ozel_ada_sayisi'] = sum(1 for a in adalar if a['kategori'] == 'OZEL')
        global_metric['kamu_ada_sayisi'] = sum(1 for a in adalar if a['kategori'] == 'KAMU')
        global_metric['tanimsiz_ada_sayisi'] = sum(1 for a in adalar if a.get('is_tanimsiz'))
        global_metric['diger_ada_sayisi'] = 0  # geri uyum
        global_metric['diger_kategori'] = diger_kategori  # tanimsizin atandigi kategori
        global_metric['diger_fonk_listesi'] = sorted(diger_fonk_sayim.items(), key=lambda x: -x[1])[:20]

        etap_metric = {}
        for eid, eb in etap_bolgeleri.items():
            e_adalar = [a for a in adalar if ada_etap_id.get(a['id']) == eid]
            m = self._hesapla_metrik(e_adalar, eb.area(), ideal_dop)
            m['ada_sayisi'] = len(e_adalar)
            m['haric_ada_sayisi'] = sum(1 for a in e_adalar if a['kategori'] == 'HARIC')
            m['ozel_ada_sayisi'] = sum(1 for a in e_adalar if a['kategori'] == 'OZEL')
            m['kamu_ada_sayisi'] = sum(1 for a in e_adalar if a['kategori'] == 'KAMU')
            m['tanimsiz_ada_sayisi'] = sum(1 for a in e_adalar if a.get('is_tanimsiz'))
            m['diger_ada_sayisi'] = 0  # geri uyum
            etap_metric[eid] = m

        crs = plan_layer.sourceCrs()

        ada_fields = self._ada_fields()
        yol_kamu_fields = self._yol_kamu_fields()
        etap_fields_def = self._etap_fields()
        tablo_fonk_fields = self._tablo_fonk_fields()
        ozet_fields = self._ozet_fields()

        sink1, dest1 = self.parameterAsSink(parameters, self.OUT_DOP_ESAS, context,
                                            ada_fields, QgsWkbTypes.MultiPolygon, crs)
        sink2, dest2 = self.parameterAsSink(parameters, self.OUT_DOP_DISI, context,
                                            ada_fields, QgsWkbTypes.MultiPolygon, crs)
        for a in adalar:
            eid = ada_etap_id.get(a['id'], -1)
            etap_alan = etap_metric[eid]['alan'] if eid in etap_metric else plan_alan
            yuzde = (a['alan'] / etap_alan * 100.0) if etap_alan > 0 else 0.0
            # DOP pay'a dahil mi? Sadece KAMU + YOL pay olur, OZEL paya degil
            # DOP_DISI ciktisi = hem hesap disi (HARIC) hem pay disi (OZEL)
            if a['kategori'] == 'KAMU':
                dop_dahil_str = 'EVET (pay)'
            elif a['kategori'] == 'OZEL':
                dop_dahil_str = 'PAYDA (pay disi)'
            else:  # HARIC
                dop_dahil_str = 'HARIC (hesap disi)'
            feat = QgsFeature(ada_fields)
            feat.setGeometry(a['geom'])
            feat.setAttributes([
                int(a['id']), a['fonk'], int(eid),
                round(a['alan'], 2),
                round(a['alan'] / nufus, 4) if nufus > 0 else 0.0,
                round(yuzde, 2),
                a['kategori'],
                dop_dahil_str,
                'EVET' if a.get('is_ay') else 'HAYIR',
            ])
            # Cikti A (DOP esas) = KAMU + tanimsiz-KAMU (paya katki yapan)
            # Cikti B (DOP disi) = OZEL + HARIC (paya katmayan)
            if a['kategori'] == 'KAMU':
                sink1.addFeature(feat, QgsFeatureSink.FastInsert)
            else:
                sink2.addFeature(feat, QgsFeatureSink.FastInsert)

        all_island_geom = QgsGeometry.unaryUnion([a['geom'] for a in adalar]) if adalar else QgsGeometry()
        yol_geom = plan_geom.difference(all_island_geom) if not all_island_geom.isEmpty() else plan_geom

        sink3, dest3 = self.parameterAsSink(parameters, self.OUT_YOL_KAMU, context,
                                            yol_kamu_fields, QgsWkbTypes.MultiPolygon, crs)
        # HARIC alanlari plan_geom'dan cikar (yol hesabi etkilenmesin)
        haric_geoms_all = [a['geom'] for a in adalar if a['kategori'] == 'HARIC']
        if haric_geoms_all:
            haric_union_all = QgsGeometry.unaryUnion(haric_geoms_all)
            # YOL'u sadece HARIC olmayan alanlar uzerinde hesapla
            yol_geom_etkin = yol_geom.difference(haric_union_all) if yol_geom else yol_geom
        else:
            yol_geom_etkin = yol_geom

        for eid, eb in etap_bolgeleri.items():
            yol_etap = yol_geom_etkin.intersection(eb) if yol_geom_etkin and not yol_geom_etkin.isEmpty() else None
            if yol_etap and not yol_etap.isEmpty() and yol_etap.area() > 1.0:
                feat = QgsFeature(yol_kamu_fields)
                feat.setGeometry(yol_etap)
                feat.setAttributes([int(eid), round(yol_etap.area(), 2), 'YOL'])
                sink3.addFeature(feat, QgsFeatureSink.FastInsert)
            # KAMU
            kamu_geoms = [a['geom'] for a in adalar
                          if ada_etap_id.get(a['id']) == eid and a['kategori'] == 'KAMU']
            if kamu_geoms:
                kamu_u = QgsGeometry.unaryUnion(kamu_geoms)
                if kamu_u and not kamu_u.isEmpty():
                    feat = QgsFeature(yol_kamu_fields)
                    feat.setGeometry(kamu_u)
                    feat.setAttributes([int(eid), round(kamu_u.area(), 2), 'KAMU'])
                    sink3.addFeature(feat, QgsFeatureSink.FastInsert)
            # OZEL (referans icin - DOP paya girmez ama paydadadir)
            ozel_geoms = [a['geom'] for a in adalar
                          if ada_etap_id.get(a['id']) == eid and a['kategori'] == 'OZEL']
            if ozel_geoms:
                ozel_u = QgsGeometry.unaryUnion(ozel_geoms)
                if ozel_u and not ozel_u.isEmpty():
                    feat = QgsFeature(yol_kamu_fields)
                    feat.setGeometry(ozel_u)
                    feat.setAttributes([int(eid), round(ozel_u.area(), 2), 'OZEL'])
                    sink3.addFeature(feat, QgsFeatureSink.FastInsert)
            # HARIC (DOP hesabindan tamamen cikar)
            haric_geoms = [a['geom'] for a in adalar
                           if ada_etap_id.get(a['id']) == eid and a['kategori'] == 'HARIC']
            if haric_geoms:
                haric_u = QgsGeometry.unaryUnion(haric_geoms)
                if haric_u and not haric_u.isEmpty():
                    feat = QgsFeature(yol_kamu_fields)
                    feat.setGeometry(haric_u)
                    feat.setAttributes([int(eid), round(haric_u.area(), 2), 'HARIC'])
                    sink3.addFeature(feat, QgsFeatureSink.FastInsert)

        sink4, dest4 = self.parameterAsSink(parameters, self.OUT_ETAP, context,
                                            etap_fields_def, QgsWkbTypes.MultiPolygon, crs)
        for eid in sorted(etap_bolgeleri.keys()):
            m = etap_metric[eid]
            feat = QgsFeature(etap_fields_def)
            feat.setGeometry(etap_bolgeleri[eid])
            feat.setAttributes([
                int(eid), round(m['alan'], 2),
                round(m.get('haric', 0), 2),
                round(m['etkin'], 2),
                round(m['ozel'], 2), round(m['kamu'], 2),
                round(m['yol'], 2), round(m['dop'], 2),
                round(m['dop_pct'], 2), round(m['sapma'], 2),
                m['durum'], round(m['acik_yesil_pct'], 2),
                m['madde9'], int(m['ada_sayisi']),
                int(m.get('haric_ada_sayisi', 0)),
                int(m.get('ozel_ada_sayisi', 0)),
                int(m.get('kamu_ada_sayisi', 0)),
            ])
            sink4.addFeature(feat, QgsFeatureSink.FastInsert)

        fonk_etap_stats = defaultdict(lambda: {'alan': 0.0, 'adet': 0,
                                                'kategori': 'KAMU', 'is_ay': False})
        for a in adalar:
            eid = ada_etap_id.get(a['id'], -1)
            key = (a['fonk'], eid)
            fonk_etap_stats[key]['alan'] += a['alan']
            fonk_etap_stats[key]['adet'] += 1
            fonk_etap_stats[key]['kategori'] = a['kategori']
            fonk_etap_stats[key]['is_ay'] = a.get('is_ay', False)

        sink5, dest5 = self.parameterAsSink(parameters, self.OUT_TABLO_FONK, context,
                                            tablo_fonk_fields, QgsWkbTypes.NoGeometry, crs)
        for (fonk, eid), d in fonk_etap_stats.items():
            etap_alan = etap_metric[eid]['alan'] if eid in etap_metric else plan_alan
            kat = d['kategori']
            if kat == 'KAMU':
                dop_str = 'EVET (pay)'
            elif kat == 'OZEL':
                dop_str = 'PAYDA (pay disi)'
            else:   # HARIC
                dop_str = 'HARIC (hesap disi)'
            feat = QgsFeature(tablo_fonk_fields)
            feat.setAttributes([
                fonk, int(eid), round(d['alan'], 2), int(d['adet']),
                round(d['alan'] / nufus, 4) if nufus > 0 else 0.0,
                round(d['alan'] / etap_alan * 100.0, 2) if etap_alan > 0 else 0.0,
                kat, dop_str,
            ])
            sink5.addFeature(feat, QgsFeatureSink.FastInsert)

        sink6, dest6 = self.parameterAsSink(parameters, self.OUT_TABLO_OZET, context,
                                            ozet_fields, QgsWkbTypes.NoGeometry, crs)
        gm = global_metric
        feat = QgsFeature(ozet_fields)
        feat.setAttributes([
            'GLOBAL', -1, round(plan_alan, 2),
            round(gm.get('haric', 0), 2),
            round(gm['etkin'], 2), round(gm['ozel'], 2),
            round(gm['kamu'], 2),
            round(gm['yol'], 2),
            round(gm['dop'], 2), round(gm['dop_pct'], 2),
            ideal_dop, round(gm['sapma'], 2), gm['durum'],
            round(gm['acik_yesil_pct'], 2), gm['madde9'],
        ])
        sink6.addFeature(feat, QgsFeatureSink.FastInsert)
        for eid in sorted(etap_metric.keys()):
            m = etap_metric[eid]
            feat = QgsFeature(ozet_fields)
            feat.setAttributes([
                'ETAP-%d' % (int(eid) + 1), int(eid), round(m['alan'], 2),
                round(m.get('haric', 0), 2),
                round(m['etkin'], 2), round(m['ozel'], 2),
                round(m['kamu'], 2),
                round(m['yol'], 2),
                round(m['dop'], 2), round(m['dop_pct'], 2),
                ideal_dop, round(m['sapma'], 2), m['durum'],
                round(m['acik_yesil_pct'], 2), m['madde9'],
            ])
            sink6.addFeature(feat, QgsFeatureSink.FastInsert)

        plugin_dir = os.path.dirname(__file__)
        feedback.pushInfo("HTML rapor hazirlaniyor (mod: %s)..." %
                          ('CDN' if html_mode == 0 else 'INLINE'))
        try:
            self._generate_html(plugin_dir, html_path, global_metric, etap_metric,
                                etap_bolgeleri, adalar, ada_etap_id, plan_geom,
                                ideal_dop, nufus, plan_alan, fonk_etap_stats,
                                crs, etap_kaynak, html_mode, feedback)
            feedback.pushInfo("HTML rapor: " + html_path)
        except Exception as e:
            import traceback
            feedback.pushInfo("UYARI: HTML rapor uretiminde hata: %s" % e)
            feedback.pushInfo(traceback.format_exc())

        return {
            self.OUT_DOP_ESAS: dest1, self.OUT_DOP_DISI: dest2,
            self.OUT_YOL_KAMU: dest3, self.OUT_ETAP: dest4,
            self.OUT_TABLO_FONK: dest5, self.OUT_TABLO_OZET: dest6,
            self.OUT_HTML: html_path,
        }

    # =========================================================
    # SINK FIELDS
    # =========================================================

    def _ada_fields(self):
        f = QgsFields()
        f.append(QgsField('ada_id', QVariant.Int))
        f.append(QgsField('uip_fonksiyon', QVariant.String))
        f.append(QgsField('etap_id', QVariant.Int))
        f.append(QgsField('alan_m2', QVariant.Double))
        f.append(QgsField('m2_per_kisi', QVariant.Double))
        f.append(QgsField('yuzde_etap', QVariant.Double))
        f.append(QgsField('kategori', QVariant.String))  # OZEL / KAMU / DIGER
        f.append(QgsField('dop_dahil', QVariant.String))  # EVET / HAYIR
        f.append(QgsField('acik_yesil', QVariant.String))  # EVET / HAYIR
        return f

    def _yol_kamu_fields(self):
        f = QgsFields()
        f.append(QgsField('etap_id', QVariant.Int))
        f.append(QgsField('alan_m2', QVariant.Double))
        f.append(QgsField('tip', QVariant.String))
        return f

    def _etap_fields(self):
        f = QgsFields()
        f.append(QgsField('etap_id', QVariant.Int))
        f.append(QgsField('alan_m2', QVariant.Double))
        f.append(QgsField('haric_alan_m2', QVariant.Double))
        f.append(QgsField('etkin_alan_m2', QVariant.Double))
        f.append(QgsField('ozel_alan_m2', QVariant.Double))
        f.append(QgsField('kamu_alan_m2', QVariant.Double))
        f.append(QgsField('yol_alan_m2', QVariant.Double))
        f.append(QgsField('dop_alan_m2', QVariant.Double))
        f.append(QgsField('dop_orani_pct', QVariant.Double))
        f.append(QgsField('hedef_sapma_pp', QVariant.Double))
        f.append(QgsField('durum', QVariant.String))
        f.append(QgsField('acik_yesil_orani_pct', QVariant.Double))
        f.append(QgsField('madde9_uyumu', QVariant.String))
        f.append(QgsField('ada_sayisi', QVariant.Int))
        f.append(QgsField('haric_ada_say', QVariant.Int))
        f.append(QgsField('ozel_ada_say', QVariant.Int))
        f.append(QgsField('kamu_ada_say', QVariant.Int))
        return f

    def _tablo_fonk_fields(self):
        f = QgsFields()
        f.append(QgsField('fonksiyon', QVariant.String))
        f.append(QgsField('etap_id', QVariant.Int))
        f.append(QgsField('alan_m2', QVariant.Double))
        f.append(QgsField('ada_sayisi', QVariant.Int))
        f.append(QgsField('m2_per_kisi', QVariant.Double))
        f.append(QgsField('yuzde_etap_alan', QVariant.Double))
        f.append(QgsField('kategori', QVariant.String))
        f.append(QgsField('dop_dahil', QVariant.String))
        return f

    def _ozet_fields(self):
        f = QgsFields()
        f.append(QgsField('kapsam', QVariant.String))
        f.append(QgsField('etap_id', QVariant.Int))
        f.append(QgsField('toplam_alan_m2', QVariant.Double))
        f.append(QgsField('haric_alan_m2', QVariant.Double))
        f.append(QgsField('etkin_alan_m2', QVariant.Double))
        f.append(QgsField('ozel_alan_m2', QVariant.Double))
        f.append(QgsField('kamu_alan_m2', QVariant.Double))
        f.append(QgsField('yol_alan_m2', QVariant.Double))
        f.append(QgsField('dop_alan_m2', QVariant.Double))
        f.append(QgsField('dop_orani_pct', QVariant.Double))
        f.append(QgsField('ideal_dop_pct', QVariant.Double))
        f.append(QgsField('sapma_pp', QVariant.Double))
        f.append(QgsField('durum', QVariant.String))
        f.append(QgsField('acik_yesil_pct', QVariant.Double))
        f.append(QgsField('madde9_uyumu', QVariant.String))
        return f

    def _sink_dop_esas(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_DOP_ESAS, context,
                                    self._ada_fields(), QgsWkbTypes.MultiPolygon, crs)

    def _sink_dop_disi(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_DOP_DISI, context,
                                    self._ada_fields(), QgsWkbTypes.MultiPolygon, crs)

    def _sink_yol_kamu(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_YOL_KAMU, context,
                                    self._yol_kamu_fields(), QgsWkbTypes.MultiPolygon, crs)

    def _sink_etap(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_ETAP, context,
                                    self._etap_fields(), QgsWkbTypes.MultiPolygon, crs)

    def _sink_tablo_fonk(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_TABLO_FONK, context,
                                    self._tablo_fonk_fields(), QgsWkbTypes.NoGeometry, crs)

    def _sink_ozet(self, parameters, context, crs):
        return self.parameterAsSink(parameters, self.OUT_TABLO_OZET, context,
                                    self._ozet_fields(), QgsWkbTypes.NoGeometry, crs)

    # =========================================================
    # METRIK
    # =========================================================

    def _hesapla_metrik(self, adalar, plan_alan, ideal_dop, diger_dop_dahil=None):
        """
        Yeni formul (kullanici tanimi):
          PO   = plan_alan (plan onama alani)
          K    = KAMU adalarin toplam alani
          O    = OZEL adalarin toplam alani
          H    = HARIC adalarin toplam alani (DOP hesabindan tamamen cikar)
          YOL  = PO - (K + O + H)
          ETKIN ALAN (payda) = PO - H
          DOP ALAN (pay)     = K + YOL
          DOP ORANI = DOP ALAN / ETKIN ALAN x 100
        """
        haric = sum(a['alan'] for a in adalar if a['kategori'] == 'HARIC')
        ozel = sum(a['alan'] for a in adalar if a['kategori'] == 'OZEL')
        kamu = sum(a['alan'] for a in adalar if a['kategori'] == 'KAMU')
        ada_total = haric + ozel + kamu
        yol = max(plan_alan - ada_total, 0.0)

        etkin = plan_alan - haric       # payda
        dop = kamu + yol                # pay
        dop_pct = (dop / etkin * 100.0) if etkin > 0 else 0.0
        sapma = dop_pct - ideal_dop
        if dop_pct < ideal_dop - 5:
            durum = 'YETERSIZ'
        elif dop_pct > ideal_dop + 5:
            durum = 'FAZLA'
        else:
            durum = 'IDEAL'

        ay_alan = sum(a['alan'] for a in adalar if a.get('is_ay'))
        ay_pct = (ay_alan / dop * 100.0) if dop > 0 else 0.0
        madde9 = 'UYUMLU' if ay_pct >= 75.0 else 'YETERSIZ'

        return {
            'alan': plan_alan,
            'haric': haric,
            'ozel': ozel, 'kamu': kamu,
            'diger': 0.0,   # geriye-uyum (artik kategori yok, hep 0)
            'yol': yol, 'etkin': etkin, 'dop': dop,
            'dop_pct': dop_pct, 'sapma': sapma, 'durum': durum,
            'acik_yesil': ay_alan, 'acik_yesil_pct': ay_pct, 'madde9': madde9,
        }

    # =========================================================
    # ETAPLAMA (kullanici + otomatik)
    # =========================================================

    def _etap_from_layer(self, etap_layer, plan_geom, feedback):
        out = {}
        eid = 0
        for f in etap_layer.getFeatures():
            g = f.geometry()
            if not g or g.isEmpty():
                continue
            g_clip = g.intersection(plan_geom)
            if g_clip and not g_clip.isEmpty() and g_clip.area() > 1.0:
                out[eid] = g_clip
                eid += 1
        if not out:
            feedback.pushInfo("UYARI: Etaplama katmani plan sinirini hic kesmiyor.")
        return out

    def _etap_otomatik(self, adalar, plan_geom, k, feedback):
        if k <= 1 or len(adalar) <= 1:
            return {0: plan_geom}

        points, weights, ref = [], [], []
        for a in adalar:
            # HARIC adalari kuvvetli sekilde dusur (etaplama belirleme etkilesini azalt)
            if a['kategori'] == 'HARIC':
                w_mult = 0.1
            elif a['kategori'] == 'OZEL':
                w_mult = 0.6
            else:  # KAMU
                w_mult = 1.0
            c = a['geom'].centroid()
            if c and not c.isEmpty():
                pt = c.asPoint()
                points.append((pt.x(), pt.y()))
                weights.append(max(a['alan'] * w_mult, 1.0))
                ref.append(a)
        if not points:
            return {0: plan_geom}

        feedback.pushInfo("Alan-agirlikli k-means: %d ada -> %d kume" % (len(points), k))
        labels, centers = area_weighted_kmeans(points, weights, k)

        cluster_polys = defaultdict(list)
        for i, lab in enumerate(labels):
            cluster_polys[lab].append(ref[i]['geom'])

        all_islands = QgsGeometry.unaryUnion([a['geom'] for a in adalar])
        bosluk_geom = plan_geom.difference(all_islands) if not all_islands.isEmpty() else QgsGeometry(plan_geom)

        bosluk_parts = []
        if bosluk_geom and not bosluk_geom.isEmpty():
            if bosluk_geom.isMultipart():
                try:
                    coll = bosluk_geom.asGeometryCollection()
                    for g in coll:
                        if g and not g.isEmpty() and g.area() > 0.1:
                            bosluk_parts.append(g)
                except Exception:
                    bosluk_parts.append(bosluk_geom)
            else:
                bosluk_parts.append(bosluk_geom)

        c_xy = {ci: c for ci, c in enumerate(centers)}
        cluster_bosluk = defaultdict(list)
        for bp in bosluk_parts:
            bc = bp.centroid().asPoint()
            best_ci = min(c_xy.keys(),
                          key=lambda c: (c_xy[c][0] - bc.x()) ** 2 + (c_xy[c][1] - bc.y()) ** 2)
            cluster_bosluk[best_ci].append(bp)

        out = {}
        for ci in cluster_polys.keys():
            parts = cluster_polys[ci] + cluster_bosluk.get(ci, [])
            if not parts:
                continue
            u = QgsGeometry.unaryUnion(parts)
            u = u.intersection(plan_geom)
            if u and not u.isEmpty() and u.area() > 1.0:
                out[ci] = u

        renumbered = {}
        for new_id, old_id in enumerate(sorted(out.keys())):
            renumbered[new_id] = out[old_id]
        return renumbered

    def _adalari_etaplara_ata(self, adalar, etap_bolgeleri):
        eid_list = list(etap_bolgeleri.keys())
        eid_centroids = {eid: etap_bolgeleri[eid].centroid().asPoint() for eid in eid_list}
        result = {}
        for a in adalar:
            ac = a['geom'].centroid()
            assigned = None
            for eid in eid_list:
                eb = etap_bolgeleri[eid]
                if eb.contains(ac) or eb.intersects(ac):
                    assigned = eid
                    break
            if assigned is None:
                acp = ac.asPoint()
                assigned = min(eid_list,
                               key=lambda e: (eid_centroids[e].x() - acp.x()) ** 2 +
                                             (eid_centroids[e].y() - acp.y()) ** 2)
            result[a['id']] = assigned
        return result

    # HTML uretimi (ayri sinifa bolundu)
    def _generate_html(self, *args, **kwargs):
        builder = _HtmlReportBuilder(self)
        builder.generate(*args, **kwargs)

    # =========================================================
    # METADATA
    # =========================================================

    def name(self):
        return '8_uip_duzenleme_ortaklik_payi'

    def displayName(self):
        return '8. Düzenleme Ortaklık Payı (DOP) Elite Analizi (UİP)'

    def group(self):
        return 'UİP Plan Analiz Araçları'

    def groupId(self):
        return 'uip_plan_analiz_araclari'

    def createInstance(self):
        return DuzenlemeOrtaklikPayiUIP()

    def shortHelpString(self):
        return (
            "<h3>Düzenleme Ortaklık Payı (DOP) Elite Analiz Aracı</h3>"
            "<p>3194 sayılı İmar Kanunu 18. madde kapsamında DOP analizini; "
            "<b>master uip_fonksiyon listesinden tiklenebilir kategori seçimi</b>, "
            "<b>etaplama (alt bölge) bazlı</b> analiz, ve "
            "<b>mekansal vektör çıktılar + interaktif HTML dashboard</b> ile gerçekleştirir.</p>"
            "<h4>Yeni Kategori Sistemi (Üç Tiklenebilir Liste — 241 master fonksiyon)</h4>"
            "<ul>"
            "<li><b>HARİÇ</b>: DOP hesabından TAMAMEN çıkar (pay+payda dışı). Sit, koruma kuşağı, "
            "sınır şeritleri, askeri yasak bölge, idari sınırlar. Default tikli.</li>"
            "<li><b>ÖZEL</b>: Etkin alana (payda) dahildir ama DOP pay'ına girmez. Konut, "
            "ticaret, turizm, sanayi, özel sağlık/eğitim/sosyal vb. Default tikli.</li>"
            "<li><b>KAMU DONATI</b>: DOP pay'ına ve payda'sına dahildir. Park, okul, hastane, "
            "ibadet, otopark, altyapı vb. Default tikli.</li>"
            "</ul>"
            "<h4>Formül</h4>"
            "<pre>PO = Plan Onama Alanı\n"
            "H  = HARİÇ adalar alanı\n"
            "O  = ÖZEL adalar alanı\n"
            "K  = KAMU DONATI adalar alanı\n"
            "YOL = PO − (H + O + K)\n\n"
            "Etkin Alan (payda) = PO − H\n"
            "DOP Alan   (pay)   = K + YOL\n"
            "<b>DOP Oranı = (K + YOL) / (PO − H) × 100   (hedef: %45)</b></pre>"
            "<h4>Çıktılar</h4>"
            "<ol>"
            "<li>DOP Esas Alanlar (KAMU adalar, poligon)</li>"
            "<li>DOP Dışı Alanlar (OZEL + HARIC adalar, poligon)</li>"
            "<li>Yol/Kamu/Özel/Hariç Alanları (poligon, etap bazında)</li>"
            "<li>Etaplama Alt Bölgeleri (poligon + metrikler)</li>"
            "<li>Fonksiyon × Etap Tablosu</li>"
            "<li>DOP Oran Özet Tablosu (Global + Etap)</li>"
            "<li>HTML Dashboard (Plotly + Leaflet, 11 grafik + harita + 6 sekme)</li>"
            "</ol>"
            "<h4>9. Madde Kontrolü</h4>"
            "<p>Açık ve yeşil alanların (park, çocuk bahçesi, meydan, semt spor alanı) "
            "toplam DOP içindeki payı <b>%75</b> altına düşmemelidir.</p>"
        )


# ===================================================================
# HTML RAPOR BUILDER
# Ayri sinifta tutuldu: HTML sablonu cok uzun, ana algoritmayi temiz tutmak icin.
# ===================================================================

class _HtmlReportBuilder:
    def __init__(self, parent_alg):
        self.alg = parent_alg

    def generate(self, plugin_dir, html_path, global_m, etap_m, etap_bolgeleri,
                 adalar, ada_etap_id, plan_geom, ideal_dop, nufus, plan_alan,
                 fonk_etap_stats, crs, etap_kaynak, html_mode, feedback):
        # html_mode: 0 = CDN (default, hafif); 1 = INLINE (offline embed)
        if html_mode == 1:
            assets_dir = _assets_dir(plugin_dir)
            _ensure_asset(assets_dir, PLOTLY_FILENAME, PLOTLY_URL, feedback)
            _ensure_asset(assets_dir, LEAFLET_JS_FILENAME, LEAFLET_JS_URL, feedback)
            _ensure_asset(assets_dir, LEAFLET_CSS_FILENAME, LEAFLET_CSS_URL, feedback)

            plotly_c = _load_asset(assets_dir, PLOTLY_FILENAME)
            leaflet_js_c = _load_asset(assets_dir, LEAFLET_JS_FILENAME)
            leaflet_css_c = _load_asset(assets_dir, LEAFLET_CSS_FILENAME)

            plotly_tag = (
                '<script>' + plotly_c + '</script>' if plotly_c
                else '<script src="' + PLOTLY_URL + '"></script>')
            leaflet_js_tag = (
                '<script>' + leaflet_js_c + '</script>' if leaflet_js_c
                else '<script src="' + LEAFLET_JS_URL + '"></script>')
            leaflet_css_tag = (
                '<style>' + leaflet_css_c + '</style>' if leaflet_css_c
                else '<link rel="stylesheet" href="' + LEAFLET_CSS_URL + '"/>')
        else:
            # CDN modu - cok daha hafif HTML, internet gerekir
            plotly_tag = '<script src="' + PLOTLY_URL + '"></script>'
            leaflet_js_tag = '<script src="' + LEAFLET_JS_URL + '"></script>'
            leaflet_css_tag = '<link rel="stylesheet" href="' + LEAFLET_CSS_URL + '"/>'

        wgs84 = QgsCoordinateReferenceSystem('EPSG:4326')
        xform = QgsCoordinateTransform(crs, wgs84, QgsProject.instance())

        def to_geojson(geom):
            g = QgsGeometry(geom)
            from contextlib import suppress
            with suppress(Exception):
                g.transform(xform)
            try:
                return json.loads(g.asJson())
            except Exception:
                return None

        etap_features = []
        for eid in sorted(etap_bolgeleri.keys()):
            eb = etap_bolgeleri[eid]
            m = etap_m[eid]
            gj = to_geojson(eb)
            if gj is None:
                continue
            etap_features.append({
                'type': 'Feature',
                'properties': {
                    'etap_id': int(eid),
                    'dop_orani': round(m['dop_pct'], 2),
                    'durum': m['durum'],
                    'alan_m2': round(m['alan'], 2),
                    'haric_alan': round(m.get('haric', 0), 2),
                    'etkin_alan': round(m['etkin'], 2),
                    'ozel_alan': round(m['ozel'], 2),
                    'kamu_alan': round(m['kamu'], 2),
                    'yol_alan': round(m['yol'], 2),
                    'sapma': round(m['sapma'], 2),
                    'acik_yesil_pct': round(m['acik_yesil_pct'], 2),
                    'madde9': m['madde9'],
                    'ada_sayisi': int(m['ada_sayisi']),
                    'haric_ada_say': int(m.get('haric_ada_sayisi', 0)),
                    'ozel_ada_say': int(m.get('ozel_ada_sayisi', 0)),
                    'kamu_ada_say': int(m.get('kamu_ada_sayisi', 0)),
                },
                'geometry': gj,
            })

        ada_features = []
        for a in adalar:
            gj = to_geojson(a['geom'])
            if gj is None:
                continue
            ada_features.append({
                'type': 'Feature',
                'properties': {
                    'id': int(a['id']),
                    'fonksiyon': a['fonk'],
                    'etap_id': int(ada_etap_id.get(a['id'], -1)),
                    'alan_m2': round(a['alan'], 2),
                    'kategori': a['kategori'],
                    'dop_dahil': a['kategori'] != 'OZEL',
                    'is_kamu': a['kategori'] == 'KAMU',
                    'is_ay': bool(a.get('is_ay')),
                },
                'geometry': gj,
            })

        plan_gj = to_geojson(plan_geom)

        etap_ids = sorted(etap_m.keys())
        etap_labels_arr = ['Etap-%d' % (int(e) + 1) for e in etap_ids]
        dop_oranlari = [round(etap_m[e]['dop_pct'], 2) for e in etap_ids]
        etkin_alanlari = [round(etap_m[e]['etkin'], 2) for e in etap_ids]
        ozel_alanlari = [round(etap_m[e]['ozel'], 2) for e in etap_ids]
        yol_alanlari = [round(etap_m[e]['yol'], 2) for e in etap_ids]
        kamu_alanlari = [round(etap_m[e]['kamu'], 2) for e in etap_ids]
        haric_alanlari = [round(etap_m[e].get('haric', 0), 2) for e in etap_ids]
        diger_alanlari = haric_alanlari  # geri uyum
        sapma_arr = [round(etap_m[e]['sapma'], 2) for e in etap_ids]
        acik_yesil_arr = [round(etap_m[e]['acik_yesil_pct'], 2) for e in etap_ids]
        ada_sayilari = [int(etap_m[e]['ada_sayisi']) for e in etap_ids]

        # DOP PAY'a giren fonksiyonlar (sadece KAMU)
        fonk_alan_total = defaultdict(float)
        for (fonk, eid), d in fonk_etap_stats.items():
            if d.get('kategori') != 'KAMU' or not fonk:
                continue
            fonk_alan_total[fonk] += d['alan']
        fonk_sorted = sorted(fonk_alan_total.items(), key=lambda x: -x[1])[:12]
        top_fonk_isim = [k for k, _ in fonk_sorted]
        top_fonk_alan = [round(v, 2) for _, v in fonk_sorted]

        heatmap_z = [[0.0] * len(etap_ids) for _ in top_fonk_isim]
        for (fonk, eid), d in fonk_etap_stats.items():
            if d.get('kategori') != 'KAMU' or fonk not in top_fonk_isim:
                continue
            i = top_fonk_isim.index(fonk)
            if eid in etap_ids:
                j = etap_ids.index(eid)
                heatmap_z[i][j] += d['alan']
        heatmap_z = [[round(v, 2) for v in row] for row in heatmap_z]

        # OZEL fonksiyonlar (payda'ya dahil, paya degil)
        fonk_disi_alan = defaultdict(float)
        for (fonk, eid), d in fonk_etap_stats.items():
            if d.get('kategori') == 'OZEL' and fonk:
                fonk_disi_alan[fonk] += d['alan']
        disi_sorted = sorted(fonk_disi_alan.items(), key=lambda x: -x[1])[:10]

        # KAMU donati fonksiyonlari (paya katki - DOP)
        fonk_kamu_alan = defaultdict(float)
        for (fonk, eid), d in fonk_etap_stats.items():
            if d.get('kategori') == 'KAMU' and fonk:
                fonk_kamu_alan[fonk] += d['alan']
        kamu_sorted = sorted(fonk_kamu_alan.items(), key=lambda x: -x[1])[:10]

        # HARIC (hesap disi: sit, koruma vb.)
        fonk_haric_alan = defaultdict(float)
        for (fonk, eid), d in fonk_etap_stats.items():
            if d.get('kategori') == 'HARIC' and fonk:
                fonk_haric_alan[fonk] += d['alan']
        haric_sorted = sorted(fonk_haric_alan.items(), key=lambda x: -x[1])[:10]
        # Geri uyumluluk
        diger_sorted = haric_sorted

        oneri = self._oneri(global_m, ideal_dop, disi_sorted)

        data = {
            'global': {k: (round(v, 4) if isinstance(v, (int, float)) else v) for k, v in global_m.items()},
            'etap': {str(int(e)): {k: (round(v, 4) if isinstance(v, (int, float)) else v) for k, v in m.items()} for e, m in etap_m.items()},
            'plan_alan': round(plan_alan, 2),
            'ideal_dop': ideal_dop,
            'nufus': nufus,
            'etap_kaynak': etap_kaynak,
            'etap_ids': [int(e) for e in etap_ids],
            'etap_labels': etap_labels_arr,
            'dop_oranlari': dop_oranlari,
            'etkin_alanlar': etkin_alanlari,
            'ozel_alanlar': ozel_alanlari,
            'yol_alanlari': yol_alanlari,
            'kamu_alanlari': kamu_alanlari,
            'haric_alanlari': haric_alanlari,
            'diger_alanlari': diger_alanlari,  # geri uyum
            'sapma_arr': sapma_arr,
            'acik_yesil_arr': acik_yesil_arr,
            'ada_sayilari': ada_sayilari,
            'top_fonk_isim': top_fonk_isim,
            'top_fonk_alan': top_fonk_alan,
            'heatmap_z': heatmap_z,
            'disi_fonk_isim': [k for k, _ in disi_sorted],
            'disi_fonk_alan': [round(v, 2) for _, v in disi_sorted],
            'kamu_fonk_isim': [k for k, _ in kamu_sorted],
            'kamu_fonk_alan': [round(v, 2) for _, v in kamu_sorted],
            'haric_fonk_isim': [k for k, _ in haric_sorted],
            'haric_fonk_alan': [round(v, 2) for _, v in haric_sorted],
            'diger_fonk_isim': [k for k, _ in haric_sorted],   # geri uyum
            'diger_fonk_alan': [round(v, 2) for _, v in haric_sorted],
            'has_haric': len(haric_sorted) > 0,
            'has_diger': len(haric_sorted) > 0,
            'etap_geojson': {'type': 'FeatureCollection', 'features': etap_features},
            'ada_geojson': {'type': 'FeatureCollection', 'features': ada_features},
            'plan_geojson': {'type': 'Feature', 'geometry': plan_gj, 'properties': {}},
            'oneri': oneri,
            'rapor_zamani': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        data_json = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
        html = self._html_template(plotly_tag, leaflet_js_tag, leaflet_css_tag, data_json, ideal_dop)
        with open(html_path, 'w', encoding='utf-8') as fobj:
            fobj.write(html)

    def _oneri(self, gm, ideal_dop, disi_sorted):
        ay_pct = gm.get('acik_yesil_pct', 0.0)
        lines = []
        # TANIMSIZ uyarisi (master listede tikli olmayan)
        if gm.get('tanimsiz_ada_sayisi', 0) > 0:
            tn = gm['tanimsiz_ada_sayisi']
            tk = gm.get('diger_kategori', 'KAMU')
            liste = gm.get('diger_fonk_listesi', [])
            ornek = ", ".join(["%s (%d)" % (k or '<bos>', c) for k, c in liste[:5]])
            lines.append(
                "TANIMSIZ FONKSIYON UYARISI: %d adet ada master listede HARIC/OZEL/KAMU "
                "hicbirinde tikli degil. Kullanici varsayimiyla %s kategorisine atandi. "
                "Ornekler: %s. Daha dogru hesap icin ust panelde bu fonksiyonlari tikleyin." %
                (tn, tk, ornek or '—'))
        # HARIC bilgisi
        if gm.get('haric', 0) > 0:
            hpct = (gm['haric'] / gm['alan'] * 100.0) if gm['alan'] > 0 else 0
            lines.append(
                "HARIC alanlar (sit, koruma, sinir vb.): %.0f m2 (plan alanin %%%.2f'si) "
                "DOP hesabindan tamamen cikarildi. Etkin alan: %.0f m2." %
                (gm['haric'], hpct, gm['etkin']))

        if gm['dop_pct'] < ideal_dop - 5:
            lines.append(
                "DOP orani (%%%.2f) hedefin (%%%g) ALTINDA. Pay (KAMU + YOL) yetersiz; "
                "kamu donatisi (park, okul, hastane vb.) artirilarak hedef saglanabilir." %
                (gm['dop_pct'], ideal_dop))
        elif gm['dop_pct'] > ideal_dop + 5:
            fazla = gm['dop_pct'] - ideal_dop
            fazla_alan = (fazla / 100.0) * gm['etkin']
            lines.append(
                "DOP orani (%%%.2f) hedefin (%%%g) UZERINDE; fazlalik %.2f p.p (~%.0f m2). "
                "Yonetmeligin 9. maddesi uyarinca bazi kullanimlari (ozel saglik, ozel egitim, "
                "ozel kres, ozel spor, ticari fonksiyonlar vb.) %%25'i gecmeyecek bicimde "
                "'ozel alan' olarak islenip DOP yukunden cikarilabilir." %
                (gm['dop_pct'], ideal_dop, fazla, fazla_alan))
            if disi_sorted:
                lines.append("Mevcut planda en buyuk 3 ozel fonksiyon: " +
                             ", ".join(["%s (%.0f m2)" % (k, v) for k, v in disi_sorted[:3]]))
        else:
            lines.append(
                "DOP orani (%%%.2f) hedefe (%%%g) yakin; tasarim kabul edilebilir aralikta." %
                (gm['dop_pct'], ideal_dop))
        if ay_pct < 75:
            eksik = 75 - ay_pct
            lines.append(
                "DIKKAT: 9. madde geregi acik-yesil alanlarin DOP icindeki payi %%%.2f; "
                "hedef %%75'in %.2f p.p altinda. Park / cocuk bahcesi / meydan / semt spor "
                "alanlari artirilarak uyum saglanmalidir." % (ay_pct, eksik))
        else:
            lines.append(
                "9. madde uyumu saglaniyor (acik-yesil DOP icinde %%%.2f, hedef %%75)." % ay_pct)
        return "\n\n".join(lines)

    def _html_template(self, plotly_tag, leaflet_js_tag, leaflet_css_tag, data_json, ideal_dop):
        # HTML sablonu sonraki Write/Edit'te eklenir (bu metodu ayri tutuyoruz).
        return _RENDER_HTML(plotly_tag, leaflet_js_tag, leaflet_css_tag, data_json, ideal_dop)


# HTML sablonu modul seviyesinde tutuluyor (asagida)
from_module_html = None  # placeholder

def _RENDER_HTML(plotly_tag, leaflet_js_tag, leaflet_css_tag, data_json, ideal_dop):
    return _HTML_TEMPLATE.replace('__PLOTLY_TAG__', plotly_tag) \
        .replace('__LEAFLET_JS_TAG__', leaflet_js_tag) \
        .replace('__LEAFLET_CSS_TAG__', leaflet_css_tag) \
        .replace('__IDEAL_DOP__', str(ideal_dop)) \
        .replace('"__DATA_JSON__"', data_json)


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>PlanX DOP Analiz Dashboard</title>
__LEAFLET_CSS_TAG__
__PLOTLY_TAG__
__LEAFLET_JS_TAG__
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Roboto,'Helvetica Neue',sans-serif;background:#f4f6f9;color:#222;line-height:1.5;}
.header{background:linear-gradient(135deg,#0f4c81 0%,#1976d2 100%);color:#fff;padding:22px 32px;box-shadow:0 2px 10px rgba(0,0,0,.1);}
.header h1{font-size:22px;margin-bottom:4px;letter-spacing:.3px;}
.header .subtitle{opacity:.88;font-size:13px;}
.container{padding:22px;max-width:1700px;margin:auto;}
.row{display:grid;gap:16px;margin-bottom:16px;}
.row.cols-2{grid-template-columns:1fr 1fr;}
.row.cols-3{grid-template-columns:repeat(3,1fr);}
.row.cols-4{grid-template-columns:repeat(4,1fr);}
@media(max-width:900px){.row{grid-template-columns:1fr!important;}}
.card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.card h3{font-size:13px;color:#555;margin-bottom:10px;font-weight:600;border-bottom:1px solid #eaecef;padding-bottom:6px;text-transform:uppercase;letter-spacing:.4px;}
.kpi{display:flex;flex-direction:column;justify-content:center;}
.kpi .val{font-size:30px;font-weight:700;color:#0f4c81;line-height:1.1;}
.kpi .lbl{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-top:4px;}
.kpi .delta{font-size:12px;margin-top:6px;font-weight:500;}
.kpi .delta.positive{color:#2e7d32;}
.kpi .delta.negative{color:#c62828;}
.kpi .delta.neutral{color:#666;}
.status{display:inline-block;padding:3px 11px;border-radius:12px;font-size:11px;font-weight:600;letter-spacing:.3px;}
.status.IDEAL{background:#e8f5e9;color:#2e7d32;}
.status.YETERSIZ{background:#fff3e0;color:#e65100;}
.status.FAZLA{background:#ffebee;color:#c62828;}
.status.UYUMLU{background:#e8f5e9;color:#2e7d32;}
#map{height:520px;border-radius:8px;}
.legend{background:#fff;padding:9px 11px;border:1px solid #ccc;border-radius:6px;font-size:11px;line-height:1.6;}
.legend .item{display:flex;align-items:center;gap:7px;}
.legend .sw{width:14px;height:14px;border-radius:3px;border:1px solid rgba(0,0,0,.2);}
.oneri{background:#fff8e1;border-left:4px solid #ff9800;padding:14px 18px;border-radius:6px;font-size:14px;line-height:1.7;white-space:pre-line;}
.madde9{background:#e3f2fd;border-left:4px solid #1976d2;padding:14px 18px;border-radius:6px;font-size:13px;line-height:1.7;}
.kilavuz{background:#f3e5f5;border-left:4px solid #8e24aa;padding:14px 18px;border-radius:6px;font-size:13px;line-height:1.7;}
.tbl{width:100%;border-collapse:collapse;font-size:12.5px;}
.tbl th{background:#f1f3f5;color:#555;padding:8px 10px;text-align:left;border-bottom:1px solid #dee2e6;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.4px;}
.tbl td{padding:7px 10px;border-bottom:1px solid #eaecef;}
.tbl tr:hover{background:#f8f9fa;}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums;}
.footer{text-align:center;color:#888;padding:14px;font-size:11px;}
.tab-bar{display:flex;gap:3px;margin-bottom:14px;border-bottom:1px solid #dee2e6;flex-wrap:wrap;}
.tab{padding:9px 16px;background:#eef0f3;border-radius:6px 6px 0 0;cursor:pointer;font-size:13px;color:#666;font-weight:500;transition:all .15s;border:1px solid transparent;border-bottom:none;}
.tab:hover{background:#fff;color:#0f4c81;}
.tab.active{background:#fff;border-color:#dee2e6;color:#0f4c81;font-weight:600;margin-bottom:-1px;}
.tab-content{display:none;animation:fadeIn .25s;}
.tab-content.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(3px);}to{opacity:1;transform:none;}}
code{background:#f6f8fa;padding:2px 6px;border-radius:4px;font-family:Consolas,monospace;font-size:12.5px;}
pre{background:#f6f8fa;padding:12px 14px;border-radius:6px;font-family:Consolas,monospace;font-size:12.5px;line-height:1.6;overflow-x:auto;}
.flex-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:10.5px;font-weight:600;background:#eef0f3;color:#444;}
.badge.blue{background:#e3f2fd;color:#1565c0;}
.badge.green{background:#e8f5e9;color:#2e7d32;}
.badge.orange{background:#fff3e0;color:#ef6c00;}
</style>
</head>
<body>
<div class="header">
  <h1>🏛 PlanX UİP — Düzenleme Ortaklık Payı (DOP) Elite Analiz Dashboard</h1>
  <div class="subtitle">3194 sayılı İmar Kanunu 18. Madde · Etaplama bazlı detay analiz · <span id="rapor_zaman"></span> · Etaplama: <span id="etap_kaynak" class="badge blue"></span></div>
</div>
<div class="container">
  <div class="tab-bar">
    <div class="tab active" data-tab="genel">📊 Genel Bakış</div>
    <div class="tab" data-tab="etap">🗂 Etaplama Analizi</div>
    <div class="tab" data-tab="harita">🗺 Mekansal Harita</div>
    <div class="tab" data-tab="fonk">🏷 Fonksiyon Dağılımı</div>
    <div class="tab" data-tab="onerme">💡 Öneri & Yönetmelik</div>
    <div class="tab" data-tab="kilavuz">📖 Kullanım Kılavuzu</div>
  </div>

  <div class="tab-content active" data-tab="genel">
    <div id="diger_uyari" style="display:none;background:#fff3e0;border-left:4px solid #ef6c00;padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:13px;line-height:1.6;">
      <b style="color:#bf360c;">⚠ TANIMSIZ FONKSİYON UYARISI:</b> <span id="diger_uyari_text"></span>
    </div>
    <div class="row cols-4">
      <div class="card kpi"><div class="val" id="kpi_plan_alan">—</div><div class="lbl">Plan Onama Alanı (m²)</div><div class="delta neutral" id="kpi_ada_say"></div></div>
      <div class="card kpi"><div class="val" id="kpi_etkin_alan">—</div><div class="lbl">Etkin Alan (m²)</div><div class="delta neutral" id="kpi_etkin_delta"></div></div>
      <div class="card kpi"><div class="val" id="kpi_dop_orani">—</div><div class="lbl">Global DOP Oranı</div><div class="delta" id="kpi_dop_delta"></div></div>
      <div class="card kpi"><div id="kpi_durum_holder"><span class="status" id="kpi_durum_pill">—</span></div><div class="lbl" style="margin-top:9px;">DOP Durumu</div><div class="delta neutral" id="kpi_madde9"></div></div>
    </div>
    <div class="row cols-4">
      <div class="card kpi"><div class="val" id="kpi_haric_alan" style="color:#424242;">—</div><div class="lbl">HARİÇ (hesap dışı, m²)</div><div class="delta neutral" id="kpi_haric_say"></div></div>
      <div class="card kpi"><div class="val" id="kpi_ozel_alan" style="color:#ef6c00;">—</div><div class="lbl">ÖZEL (payda dahil, m²)</div><div class="delta neutral" id="kpi_ozel_say"></div></div>
      <div class="card kpi"><div class="val" id="kpi_kamu_alan" style="color:#43a047;">—</div><div class="lbl">KAMU (pay+payda, m²)</div><div class="delta neutral" id="kpi_kamu_say"></div></div>
      <div class="card kpi"><div class="val" id="kpi_yol_alan" style="color:#607d8b;">—</div><div class="lbl">YOL (pay, m²)</div><div class="delta neutral" id="kpi_yol_delta"></div></div>
    </div>
    <div class="row cols-2">
      <div class="card"><h3>1. DOP Oranı Gauge (Hedef: %__IDEAL_DOP__)</h3><div id="g1" style="height:300px;"></div></div>
      <div class="card"><h3>2. Global Alan Bileşimi</h3><div id="g2" style="height:300px;"></div></div>
    </div>
    <div class="row cols-2">
      <div class="card"><h3>3. m²/Kişi — Plan Bütünü</h3><div id="g3" style="height:280px;"></div></div>
      <div class="card"><h3>4. Açık-Yeşil Alan Payı (DOP içinde) — 9. Madde Hedefi %75</h3><div id="g4" style="height:280px;"></div></div>
    </div>
  </div>

  <div class="tab-content" data-tab="etap">
    <div class="row cols-2">
      <div class="card"><h3>5. Alt Bölge DOP Oranları</h3><div id="g5" style="height:340px;"></div></div>
      <div class="card"><h3>6. Hedef Sapma (p.p) — Alt Bölge</h3><div id="g6" style="height:340px;"></div></div>
    </div>
    <div class="row cols-2">
      <div class="card"><h3>7. Alt Bölge Alan Yığını (Yol / Kamu / Özel)</h3><div id="g7" style="height:340px;"></div></div>
      <div class="card"><h3>8. Açık-Yeşil Oranı — Alt Bölge</h3><div id="g8" style="height:340px;"></div></div>
    </div>
    <div class="card"><h3>Alt Bölge Detay Tablosu</h3><div style="overflow-x:auto;"><table class="tbl" id="etap_table"></table></div></div>
  </div>

  <div class="tab-content" data-tab="harita">
    <div class="card">
      <h3>🗺 DOP Oranı Choropleth — Alt Bölgeler (Renkler hedeften sapmayı gösterir)</h3>
      <div id="map"></div>
    </div>
  </div>

  <div class="tab-content" data-tab="fonk">
    <div class="row cols-2">
      <div class="card"><h3>9. Fonksiyon Bazlı Alan Dağılımı (DOP'a Giren - İlk 12)</h3><div id="g9" style="height:480px;"></div></div>
      <div class="card"><h3>10. Fonksiyon × Etap Heatmap (m²)</h3><div id="g10" style="height:480px;"></div></div>
    </div>
    <div class="card"><h3>11. DOP Dışı Tutulan Fonksiyonlar (Top 10)</h3><div id="g11" style="height:380px;"></div></div>
  </div>

  <div class="tab-content" data-tab="onerme">
    <div class="card"><h3>💡 Otomatik Öneri</h3><div class="oneri" id="oneri_box"></div></div>
    <div class="card">
      <h3>📜 3194 Sayılı Kanun · 9. Madde (Açık-Yeşil Alan %75 Kuralı)</h3>
      <div class="madde9">
        <p><b>İlgili Hüküm:</b> "İlçe sınırları dahilinde; komşuluk, mahalle, semt ölçeğinde veya kent bütünü ile yerleşme alanlarında açık ve yeşil alan standartları; çocuk bahçesi, oyun alanı, park, meydan, semt spor alanı, botanik parkı, mesire yeri ve rekreasyon için <b>10 m²/kişi</b> olarak uygulanacak olup, bu standardın uygulanmasında kamuya ait; düzenleme ortaklık payına tabi <b>çocuk bahçesi, oyun alanı, park, meydan ve semt spor alanları oranı toplamı %75'in altına düşürülemez.</b>"</p>
        <p style="margin-top:10px;"><b>Yorum:</b> DOP'a giren açık-yeşil kategori alanlarının, toplam DOP alanı içindeki payı en az %75 olmalıdır. Bu eşik bu raporda hem global hem her alt bölge için ayrı ayrı izlenir.</p>
      </div>
    </div>
    <div class="card">
      <h3>📜 DOP Hesabı & %45 Hedef</h3>
      <div class="madde9">
        <p><b>Formül (Yeni — kategorik):</b></p>
        <pre>PO    = Plan Onama Alanı
H     = HARİÇ adalar (sit, koruma kuşağı, sınır şeridi vb.) — TAMAMEN ÇIKAR
O     = ÖZEL adalar (konut, ticaret, turizm, sanayi, özel sağlık/eğitim vb.)
K     = KAMU DONATI adalar (park, okul, hastane, ibadet, idari, altyapı vb.)
YOL   = PO − (H + O + K)         (adalar dışı plan boşluğu)

Etkin Alan (payda) = PO − H
DOP Alan   (pay)   = K + YOL
<b>DOP Oranı = (K + YOL) / (PO − H) × 100      (hedef: %__IDEAL_DOP__)</b></pre>
        <p style="margin-top:10px;"><b>Mantık:</b> ÖZEL alanlar etkin alana (payda'ya) dahildir
        ama DOP pay'ına (K+YOL) girmez — arsa sahibinin mülkiyetinde kalır. HARİÇ alanlar
        sit/koruma/sınır şeridi gibi düzenleme dışı kullanımlar; hem pay'dan hem
        payda'dan çıkarılır.</p>
        <p style="margin-top:10px;"><b>%45 Eşiği Üzeri:</b> Bazı kullanımlar (özel sağlık tesisi, özel eğitim, özel kreş, özel spor tesisi, ticari fonksiyonlar) %25'i geçmeyecek biçimde özel mülk niteliğinde ('özel alan') işlenip DOP yükünden çıkarılarak hedef oran sağlanabilir.</p>
      </div>
    </div>
  </div>

  <div class="tab-content" data-tab="kilavuz">
    <div class="card">
      <h3>📖 Kullanım Kılavuzu — DOP Elite Aracı</h3>
      <div class="kilavuz">
        <h4 style="color:#6a1b9a;margin-bottom:6px;">1. Veri Hazırlığı</h4>
        <p>Plan onama sınırı poligonu ve fonksiyon adalarını içeren UİP plan katmanı projeye yüklenmiş olmalıdır. Plan katmanında her adanın fonksiyon adını taşıyan bir sütun bulunmalıdır (uipfonksiyon, fonksiyon vb.).</p>
        <h4 style="color:#6a1b9a;margin-top:12px;margin-bottom:6px;">2. Fonksiyon Sütunu</h4>
        <p>Araç açıldığında "Fonksiyon Sütunu" parametresi otomatik olarak plan katmanının metin tipindeki sütunlarını listeler. İstediğiniz kolonu seçin. Default değer <code>uipfonksiyon</code>'dur.</p>
        <h4 style="color:#6a1b9a;margin-top:12px;margin-bottom:6px;">3. Kategori Seçimi (3 Tiklenebilir Liste)</h4>
        <p>Master listesi 241 uip_fonksiyon değeri içerir (dop_values.gpkg). 3 ayrı tiklenebilir liste sunulur:</p>
        <ul style="padding-left:22px;">
          <li><b>HARİÇ</b>: DOP hesabından tamamen çıkar (pay+payda dışı). Default: planlama sınırları, idari sınırlar, korunacak alanlar, yapı sınırlaması koruma kuşakları, afet alanları, özel kanunlarla belirlenen alan sınırları, bugünkü arazi kullanımı korunacak gruplar.</li>
          <li><b>ÖZEL</b>: Mülkiyet arsa sahibinde, etkin alana dahil ama DOP pay'ına girmez. Default: konut, turizm, kentsel çalışmadaki ticaret/sanayi + tüm "ÖZEL ..." prefix'li kullanımlar.</li>
          <li><b>KAMU</b>: DOP pay'ına ve payda'sına dahil. Default: açık-yeşil, eğitim/sağlık/sosyal (özel olmayan), ibadet, ulaşım, enerji, su-atıksu, kentsel çalışmadan belediye/resmi/idari/pazar.</li>
        </ul>
        <h4 style="color:#6a1b9a;margin-top:12px;margin-bottom:6px;">4. Etaplama</h4>
        <p><b>(a) Kullanıcı poligonu:</b> Mevcut etaplama katmanınız varsa "Etaplama Katmanı" parametresine verin. Her poligon bir alt bölge olur.</p>
        <p style="margin-top:6px;"><b>(b) Otomatik:</b> Etap katmanı vermeden "Etaplama Sayısı" (1-20) girin. Araç <i>alan-ağırlıklı k-means + boşluk atama</i> ile etaplama bölgelerini üretir; <b>sınırlar adaların arasından geçer, hiçbir ada kesilmez.</b></p>
        <h4 style="color:#6a1b9a;margin-top:12px;margin-bottom:6px;">5. Çıktılar</h4>
        <ol style="padding-left:22px;">
          <li><b>DOP Esas Alanlar (poligon)</b> — DOP hesabına giren ada poligonları</li>
          <li><b>DOP Dışı Özel Alanlar (poligon)</b> — Hesap dışında tutulan özel ada poligonları</li>
          <li><b>Yol ve Kamu Alanları (poligon)</b> — Etap bazında yol + kamu donatı</li>
          <li><b>Etaplama Alt Bölgeleri (poligon)</b> — Her bölgenin DOP metrikleri attribute olarak</li>
          <li><b>Fonksiyon × Etap Tablosu (no-geom)</b></li>
          <li><b>DOP Oran Özet Tablosu (no-geom)</b> — Global + her etap satırı</li>
          <li><b>HTML Dashboard</b> — Bu rapor (Plotly + Leaflet, offline embed)</li>
        </ol>
        <h4 style="color:#6a1b9a;margin-top:12px;margin-bottom:6px;">6. Yorumlama</h4>
        <ul style="padding-left:22px;">
          <li><b>IDEAL</b> (yeşil): DOP oranı hedefe ±5 p.p yakın.</li>
          <li><b>YETERSIZ</b> (turuncu): DOP oranı hedeften 5 p.p+ düşük; donatı/yol artışı önerilir.</li>
          <li><b>FAZLA</b> (kırmızı): DOP oranı hedeften 5 p.p+ yüksek; özel alan dönüşümü değerlendirilebilir (9. madde, %25 sınırı).</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="footer">PlanX UİP Toolset · Geliştirici: Arş. Gör. Yusuf Eminoğlu · Dokuz Eylül Üniversitesi Şehir ve Bölge Planlama Bölümü</div>
</div>

<script>
const DATA = "__DATA_JSON__";
const IDEAL_DOP = DATA.ideal_dop;
function fmtNum(n){return (n||0).toLocaleString('tr-TR',{maximumFractionDigits:2});}
function safePlot(elId, traces, layout, conf){
  try { Plotly.newPlot(elId, traces, layout, conf); }
  catch(e){
    console.error('Plot ' + elId + ' hatasi:', e);
    const el = document.getElementById(elId);
    if (el) el.innerHTML = '<div style="padding:20px;color:#c62828;font-size:12px;">Grafik yuklenirken hata: ' + e.message + '</div>';
  }
}

document.getElementById('rapor_zaman').innerText = DATA.rapor_zamani;
document.getElementById('etap_kaynak').innerText = DATA.etap_kaynak === 'OTOMATIK' ? 'Otomatik (k-means + ada-snap)' : 'Kullanıcı Katmanı';

document.getElementById('kpi_plan_alan').innerText = fmtNum(DATA.plan_alan);
document.getElementById('kpi_ada_say').innerText = DATA.global.ada_sayisi + ' ada · ' + fmtNum(DATA.nufus) + ' kişi';
document.getElementById('kpi_etkin_alan').innerText = fmtNum(DATA.global.etkin);
const etkin_pct = (DATA.global.etkin / DATA.plan_alan * 100);
document.getElementById('kpi_etkin_delta').innerText = 'Plan onamanın %' + etkin_pct.toFixed(1) + "'i  ·  Özel: " + fmtNum(DATA.global.ozel) + ' m²';
document.getElementById('kpi_dop_orani').innerText = '%' + DATA.global.dop_pct.toFixed(2);
const dopDelta = DATA.global.dop_pct - IDEAL_DOP;
const dopDeltaEl = document.getElementById('kpi_dop_delta');
dopDeltaEl.className = 'delta ' + (Math.abs(dopDelta) < 5 ? 'positive' : 'negative');
dopDeltaEl.innerText = (dopDelta >= 0 ? '+' : '') + dopDelta.toFixed(2) + ' p.p · hedef %' + IDEAL_DOP;
const pill = document.getElementById('kpi_durum_pill');
pill.className = 'status ' + DATA.global.durum;
pill.innerText = DATA.global.durum;
document.getElementById('kpi_madde9').innerText = 'Açık-Yeşil DOP içinde %' + DATA.global.acik_yesil_pct.toFixed(1) + '  ·  9. Madde: ' + DATA.global.madde9;
document.getElementById('oneri_box').innerText = DATA.oneri;

// Kategori kirilimi KPI
document.getElementById('kpi_haric_alan').innerText = fmtNum(DATA.global.haric||0);
document.getElementById('kpi_haric_say').innerText = (DATA.global.haric_ada_sayisi||0) + ' ada · %' + ((DATA.global.haric||0)/DATA.plan_alan*100).toFixed(1);
document.getElementById('kpi_ozel_alan').innerText = fmtNum(DATA.global.ozel||0);
document.getElementById('kpi_ozel_say').innerText = (DATA.global.ozel_ada_sayisi||0) + ' ada · %' + ((DATA.global.ozel||0)/DATA.plan_alan*100).toFixed(1);
document.getElementById('kpi_kamu_alan').innerText = fmtNum(DATA.global.kamu||0);
document.getElementById('kpi_kamu_say').innerText = (DATA.global.kamu_ada_sayisi||0) + ' ada · %' + ((DATA.global.kamu||0)/DATA.plan_alan*100).toFixed(1);
document.getElementById('kpi_yol_alan').innerText = fmtNum(DATA.global.yol||0);
document.getElementById('kpi_yol_delta').innerText = 'Etkin alanın %' + ((DATA.global.yol||0)/(DATA.global.etkin||1)*100).toFixed(1) + "'i";

// TANIMSIZ uyari banner: master listede tikli olmayan adalar
if ((DATA.global.tanimsiz_ada_sayisi||0) > 0) {
  const dn = DATA.global.tanimsiz_ada_sayisi;
  const dkat = DATA.global.diger_kategori || 'KAMU';
  document.getElementById('diger_uyari_text').innerHTML =
    dn + ' adet ada master listede HARIÇ/ÖZEL/KAMU hiçbirinde tikli değil — '+
    'kullanıcı varsayımıyla <b>' + dkat + '</b> kategorisine atandı. ' +
    'Daha doğru hesap için bu fonksiyonları master listede uygun kategoriye tikleyin.';
  document.getElementById('diger_uyari').style.display = 'block';
}
// HARIC uyari (bilgi amacli)
if ((DATA.global.haric||0) > 0) {
  const haricPct = ((DATA.global.haric||0)/DATA.plan_alan*100).toFixed(2);
  console.info('HARIC (hesap disi) alan: ' + fmtNum(DATA.global.haric) + ' m2 (' + haricPct + '%) - DOP hesabindan cikarildi.');
}

document.querySelectorAll('.tab').forEach(t=>{
  t.addEventListener('click',()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    document.querySelector('.tab-content[data-tab="'+t.dataset.tab+'"]').classList.add('active');
    setTimeout(()=>{window.dispatchEvent(new Event('resize'));if(window._map)window._map.invalidateSize();},100);
  });
});

const cfg = {displayModeBar:false, responsive:true};

safePlot('g1',[{
  type:'indicator', mode:'gauge+number+delta',
  value: DATA.global.dop_pct,
  delta:{reference:IDEAL_DOP, increasing:{color:'#c62828'}, decreasing:{color:'#e65100'}},
  gauge:{
    axis:{range:[0, Math.max(80, DATA.global.dop_pct*1.2)]},
    bar:{color:'#0f4c81', thickness:0.4},
    steps:[
      {range:[0, IDEAL_DOP-5], color:'#fff3e0'},
      {range:[IDEAL_DOP-5, IDEAL_DOP+5], color:'#e8f5e9'},
      {range:[IDEAL_DOP+5, 80], color:'#ffebee'}
    ],
    threshold:{line:{color:'#000', width:3}, thickness:0.9, value:IDEAL_DOP}
  },
  number:{suffix:'%', valueformat:'.2f'}
}],{margin:{t:30,b:10,l:30,r:30}}, cfg);

const g2_lbls=['ÖZEL (payda/pay dışı)','YOL (pay)','KAMU DONATI (pay)'];
const g2_vals=[DATA.global.ozel||0, DATA.global.yol||0, DATA.global.kamu||0];
const g2_clrs=['#ef6c00','#90a4ae','#43a047'];
if ((DATA.global.haric||0) > 0) {
  g2_lbls.push('HARİÇ (hesap dışı)');
  g2_vals.push(DATA.global.haric);
  g2_clrs.push('#424242');
}
safePlot('g2',[{
  type:'pie', hole:0.55,
  labels:g2_lbls, values:g2_vals,
  marker:{colors:g2_clrs},
  textinfo:'label+percent', insidetextorientation:'radial'
}],{margin:{t:20,b:20,l:20,r:20}, showlegend:true, legend:{orientation:'h', y:-0.05}}, cfg);

const m2pkisi = {
  etkin: DATA.global.etkin / DATA.nufus,
  ozel:  DATA.global.ozel  / DATA.nufus,
  yol:   DATA.global.yol   / DATA.nufus,
  kamu:  DATA.global.kamu  / DATA.nufus
};
safePlot('g3',[{
  type:'bar', orientation:'h',
  y:['Kamu Donatı','Yol','DOP Dışı Özel','Etkin Alan'],
  x:[m2pkisi.kamu, m2pkisi.yol, m2pkisi.ozel, m2pkisi.etkin],
  marker:{color:['#43a047','#90a4ae','#ef6c00','#1976d2']},
  text:[m2pkisi.kamu.toFixed(2), m2pkisi.yol.toFixed(2), m2pkisi.ozel.toFixed(2), m2pkisi.etkin.toFixed(2)].map(v=>v+' m²/kişi'),
  textposition:'outside'
}],{margin:{t:10,b:30,l:120,r:60}, xaxis:{title:'m² / kişi'}}, cfg);

safePlot('g4',[{
  type:'indicator', mode:'gauge+number',
  value: DATA.global.acik_yesil_pct,
  gauge:{
    axis:{range:[0,100]},
    bar:{color:'#2e7d32', thickness:0.4},
    steps:[{range:[0,75], color:'#ffebee'}, {range:[75,100], color:'#e8f5e9'}],
    threshold:{line:{color:'#000', width:3}, thickness:0.9, value:75}
  },
  number:{suffix:'%', valueformat:'.1f'}
}],{margin:{t:20,b:10,l:30,r:30}}, cfg);

safePlot('g5',[{
  type:'bar', x:DATA.etap_labels, y:DATA.dop_oranlari,
  marker:{color:DATA.dop_oranlari.map(v=>Math.abs(v-IDEAL_DOP)<5?'#43a047':(v>IDEAL_DOP?'#c62828':'#fb8c00'))},
  text:DATA.dop_oranlari.map(v=>v.toFixed(1)+'%'), textposition:'outside', name:'DOP %'
},{
  type:'scatter', x:DATA.etap_labels, y:DATA.etap_labels.map(_=>IDEAL_DOP),
  mode:'lines', line:{dash:'dash', color:'#1976d2', width:2}, name:'Hedef %'+IDEAL_DOP
}],{yaxis:{title:'DOP %', range:[0, Math.max.apply(null, DATA.dop_oranlari.concat([IDEAL_DOP]))*1.25]}, margin:{t:10,b:40}, legend:{orientation:'h', y:-0.15}}, cfg);

safePlot('g6',[{
  type:'bar', y:DATA.etap_labels, x:DATA.sapma_arr, orientation:'h',
  marker:{color:DATA.sapma_arr.map(v=>v>=0?'#c62828':'#43a047')},
  text:DATA.sapma_arr.map(v=>(v>=0?'+':'')+v.toFixed(2)+' p.p'), textposition:'outside'
}],{xaxis:{title:'Sapma (p.p)', zeroline:true, zerolinewidth:2, zerolinecolor:'#333'}, margin:{t:10,l:80}}, cfg);

const g7_traces=[
  {type:'bar', x:DATA.etap_labels, y:DATA.kamu_alanlari, name:'KAMU (pay)', marker:{color:'#43a047'}},
  {type:'bar', x:DATA.etap_labels, y:DATA.yol_alanlari, name:'YOL (pay)', marker:{color:'#90a4ae'}},
  {type:'bar', x:DATA.etap_labels, y:DATA.ozel_alanlari, name:'ÖZEL (payda)', marker:{color:'#ef6c00'}}
];
if ((DATA.haric_alanlari||[]).some(v=>v>0)) {
  g7_traces.push({type:'bar', x:DATA.etap_labels, y:DATA.haric_alanlari, name:'HARİÇ (hesap dışı)', marker:{color:'#424242'}});
}
safePlot('g7', g7_traces, {barmode:'stack', yaxis:{title:'Alan (m²)'}, margin:{t:10,b:40}, legend:{orientation:'h', y:-0.15}}, cfg);

safePlot('g8',[{
  type:'bar', x:DATA.etap_labels, y:DATA.acik_yesil_arr,
  marker:{color:DATA.acik_yesil_arr.map(v=>v>=75?'#43a047':'#c62828')},
  text:DATA.acik_yesil_arr.map(v=>v.toFixed(1)+'%'), textposition:'outside', name:'Açık-Yeşil %'
},{
  type:'scatter', x:DATA.etap_labels, y:DATA.etap_labels.map(_=>75),
  mode:'lines', line:{dash:'dash', color:'#1976d2', width:2}, name:'Hedef %75'
}],{yaxis:{title:'% (DOP içinde Açık-Yeşil)', range:[0,Math.max(100, Math.max.apply(null, DATA.acik_yesil_arr.concat([75]))*1.1)]}, margin:{t:10,b:40}, legend:{orientation:'h', y:-0.15}}, cfg);

let tblHTML = '<thead><tr><th>Etap</th><th>Toplam (m²)</th><th>Hariç (m²)</th><th>Etkin (m²)</th><th>Özel (m²)</th><th>Kamu (m²)</th><th>Yol (m²)</th><th>DOP (m²)</th><th>DOP %</th><th>Sapma</th><th>Durum</th><th>Açık-Yeşil %</th><th>9. Madde</th><th>Ada</th></tr></thead><tbody>';
DATA.etap_ids.forEach((eid,i)=>{
  const m = DATA.etap[String(eid)];
  tblHTML += '<tr>'+
    '<td><b>Etap-'+(eid+1)+'</b></td>'+
    '<td class="num">'+fmtNum(m.alan)+'</td>'+
    '<td class="num">'+fmtNum(m.haric||0)+'</td>'+
    '<td class="num">'+fmtNum(m.etkin)+'</td>'+
    '<td class="num">'+fmtNum(m.ozel)+'</td>'+
    '<td class="num">'+fmtNum(m.kamu)+'</td>'+
    '<td class="num">'+fmtNum(m.yol)+'</td>'+
    '<td class="num">'+fmtNum(m.dop)+'</td>'+
    '<td class="num"><b>'+m.dop_pct.toFixed(2)+'%</b></td>'+
    '<td class="num">'+(m.sapma>=0?'+':'')+m.sapma.toFixed(2)+'</td>'+
    '<td><span class="status '+m.durum+'">'+m.durum+'</span></td>'+
    '<td class="num">'+m.acik_yesil_pct.toFixed(1)+'%</td>'+
    '<td><span class="status '+(m.madde9==='UYUMLU'?'UYUMLU':'FAZLA')+'">'+m.madde9+'</span></td>'+
    '<td class="num">'+m.ada_sayisi+'</td>'+
  '</tr>';
});
tblHTML += '</tbody>';
document.getElementById('etap_table').innerHTML = tblHTML;

safePlot('g9',[{
  type:'bar', x:DATA.top_fonk_alan, y:DATA.top_fonk_isim, orientation:'h',
  marker:{color:'#0f4c81'},
  text:DATA.top_fonk_alan.map(v=>fmtNum(v)+' m²'), textposition:'outside'
}],{margin:{t:10,l:260,b:40,r:60}, xaxis:{title:'Alan (m²)'}, yaxis:{autorange:'reversed'}}, cfg);

safePlot('g10',[{
  type:'heatmap', x:DATA.etap_labels, y:DATA.top_fonk_isim, z:DATA.heatmap_z,
  colorscale:'Blues', hovertemplate:'%{x}<br>%{y}<br>%{z:,.0f} m²<extra></extra>',
  showscale:true, colorbar:{title:'m²'}
}],{margin:{t:10,l:260,b:60,r:40}, yaxis:{autorange:'reversed'}}, cfg);

safePlot('g11',[{
  type:'bar', x:DATA.disi_fonk_alan, y:DATA.disi_fonk_isim, orientation:'h',
  marker:{color:'#ef6c00'},
  text:DATA.disi_fonk_alan.map(v=>fmtNum(v)+' m²'), textposition:'outside'
}],{margin:{t:10,l:260,b:40,r:60}, xaxis:{title:'Alan (m²)'}, yaxis:{autorange:'reversed'}}, cfg);

const map = L.map('map');
window._map = map;
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap', maxZoom:19}).addTo(map);
function getColor(dopPct){
  const diff = Math.abs(dopPct - IDEAL_DOP);
  if (diff<3) return '#1b5e20';
  if (diff<6) return '#43a047';
  if (diff<10) return '#ffa000';
  return '#c62828';
}
const etapLayer = L.geoJSON(DATA.etap_geojson,{
  style: f=>({color:'#fff', weight:2.5, fillColor:getColor(f.properties.dop_orani), fillOpacity:0.7}),
  onEachFeature:(f,layer)=>{
    const p = f.properties;
    layer.bindPopup(
      '<div style="font-size:13px;min-width:220px;">'+
      '<div style="font-weight:600;font-size:14px;color:#0f4c81;border-bottom:1px solid #eee;padding-bottom:5px;margin-bottom:6px;">Etap-'+(p.etap_id+1)+'</div>'+
      '<div>Toplam Alan: <b>'+fmtNum(p.alan_m2)+' m²</b></div>'+
      '<div>Etkin Alan: <b>'+fmtNum(p.etkin_alan)+' m²</b></div>'+
      '<div>DOP Oranı: <b style="color:'+getColor(p.dop_orani)+';">'+p.dop_orani.toFixed(2)+'%</b> (sapma '+p.sapma+')</div>'+
      '<div>Durum: <b>'+p.durum+'</b></div>'+
      '<div>Açık-Yeşil: '+p.acik_yesil_pct+'% ('+p.madde9+')</div>'+
      '<div>Ada sayısı: '+p.ada_sayisi+'</div>'+
      '</div>'
    );
  }
}).addTo(map);
const adaLayer = L.geoJSON(DATA.ada_geojson,{
  style:f=>({color: f.properties.dop_dahil?'#1976d2':'#ef6c00', weight:0.8, fillOpacity:0.2}),
  onEachFeature:(f,layer)=>{
    const p = f.properties;
    layer.bindTooltip('<b>'+p.fonksiyon+'</b><br>'+fmtNum(p.alan_m2)+' m² · Etap-'+(p.etap_id+1), {sticky:true});
  }
}).addTo(map);
try { map.fitBounds(etapLayer.getBounds(), {padding:[16,16]}); }
catch(e){ map.setView([39, 35], 6); }

const legend = L.control({position:'bottomright'});
legend.onAdd = function(){
  const div = L.DomUtil.create('div','legend');
  div.innerHTML = '<b>DOP Sapma (Hedef %'+IDEAL_DOP+')</b>'+
    '<div class="item"><span class="sw" style="background:#1b5e20"></span> < ±3 p.p (Mükemmel)</div>'+
    '<div class="item"><span class="sw" style="background:#43a047"></span> < ±6 p.p (İyi)</div>'+
    '<div class="item"><span class="sw" style="background:#ffa000"></span> < ±10 p.p (Orta)</div>'+
    '<div class="item"><span class="sw" style="background:#c62828"></span> > ±10 p.p (Kritik)</div>'+
    '<hr style="margin:6px 0;border:none;border-top:1px solid #eee">'+
    '<div class="item"><span class="sw" style="background:#1976d2;opacity:0.4"></span> DOP Dahil Ada</div>'+
    '<div class="item"><span class="sw" style="background:#ef6c00;opacity:0.4"></span> DOP Dışı Ada</div>';
  return div;
};
legend.addTo(map);
</script>
</body>
</html>"""
