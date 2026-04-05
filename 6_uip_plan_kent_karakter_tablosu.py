# File: 6_uip_plan_kent_karakter_tablosu.py
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsWkbTypes,
    QgsFeatureSink,
    QgsProcessingUtils
)
from qgis.PyQt.QtCore import QVariant
import processing

class PlanKentKarakterTablosuUIP(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('plan_onama_siniri', 'Plan Onama Sınırı (Poligon)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterVectorLayer('plan_katmani', 'UİP Plan Katmanı (Fonksiyonlar)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterNumber('plan_nufusu', 'Plan Nüfusu', QgsProcessingParameterNumber.Double, minValue=1.0))
        self.addParameter(QgsProcessingParameterFeatureSink('output', 'Çıktı: 6. UİP Kent Karakter Tablosu', type=QgsProcessing.TypeVectorAnyGeometry))

    def processAlgorithm(self, parameters, context, feedback):
        sinir_layer = self.parameterAsVectorLayer(parameters, 'plan_onama_siniri', context)
        plan_layer = self.parameterAsVectorLayer(parameters, 'plan_katmani', context)
        plan_nufusu = self.parameterAsDouble(parameters, 'plan_nufusu', context)

        feedback.pushInfo("1. Plan katmanı onama sınırına göre kesiliyor (Clip)...")
        clipped_result = processing.run(
            "native:clip",
            {'INPUT': plan_layer.source(), 'OVERLAY': sinir_layer.source(), 'OUTPUT': 'TEMPORARY_OUTPUT'},
            context=context, feedback=feedback, is_child_algorithm=True
        )
        clipped_id = clipped_result['OUTPUT']
        clipped = QgsProcessingUtils.mapLayerFromString(clipped_id, context)

        lookup = {
            'AĞAÇLANDIRILACAK ALAN': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101001'),
            'ARBORETUM - BOTANİK PARKI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101002'),
            'ÇOCUK BAHÇESİ VE OYUN ALANI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101003'),
            'FUAR, PANAYIR VE FESTİVAL ALANI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101004'),
            'HAYVANAT BAHÇESİ': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101005'),
            'HİPODROM': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101006'),
            'KENT ORMANI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101007'),
            'KORUNACAK BAHÇE': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101008'),
            'MESİRE YERİ': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101009'),
            'MEYDAN': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101010'),
            'MEZARLIK ALANI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101011'),
            'MİLLET BAHÇESİ': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101012'),
            'PARK': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101013'),
            'PASİF YEŞİL ALAN': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101014'),
            'REKREASYON ALANI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101015'),
            'REKREAKTİF ALAN': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101016'),
            'BAKI VE SEYİR TERASI': ('101000', 'AÇIK VE YEŞİL ALANLAR', '101017'),
            'DOĞAL KARAKTERİ KORUNACAK ALAN': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103003'),
            'KUMSAL-PLAJ': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103004'),
            'MAKİLİK- FUNDALIK ALAN': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103005'),
            'MERA ALANI': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103006'),
            'ORGANİK TARIM ALANI': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103007'),
            'ORMAN ALANI': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103008'),
            'ÖRTÜ ALTI TARIM ARAZİSİ': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103009'),
            'TARIMSAL NİTELİKLİ ALAN': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103010'),
            'ZEYTİNLİK ALAN': ('103000', 'BUGÜNKÜ ARAZİ KULLANIMI DEVAM ETTİRİLEREK KORUNACAK ALANLAR', '103011'),
            'ANA İSTASYON (GAR)': ('104000', 'DEMİRYOLLARI', '104001'),
            'ARA İSTASYON': ('104000', 'DEMİRYOLLARI', '104002'),
            'ANAOKULU ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105001'),
            'HALK EĞİTİM MERKEZİ': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105002'),
            'İLKOKUL ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105003'),
            'LİSE ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105004'),
            'ORTAOKUL ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105005'),
            'ÖZEL ANAOKULU ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105006'),
            'ÖZEL EĞİTİM ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105007'),
            'MESLEKİ VE TEKNİK ÖĞRETİM TESİSİ ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105008'),
            'YÜKSEK ÖĞRETİM ALANI': ('105000', 'EĞİTİM TESİSLERİ ALANI', '105009'),
            'AKARYAKIT ÜRÜNLERİ DEPOLAMA ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106001'),
            'DOĞALGAZ / DAĞITIM TESİSİ ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106002'),
            'ENERJİ ÜRETİM ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106003'),
            'ELEKTRONİK HABERLEŞME ALTYAPI ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106004'),
            'NÜKLEER ENERJİ SANTRALİ ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106005'),
            'REGÜLATÖR ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106006'),
            'TERMİK SANTRAL ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106007'),
            'TRAFO ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106008'),
            'TÜRBİN ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106009'),
            'YANICI PARLAYICI VE PATLAYICI MADDELER ÜRETİM VE DEPO ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106010'),
            'YENİLENEBİLİR ENERJİ KAYNAKLARINA DAYALI ÜRETİM TESİSİ ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106011'),
            'HAVAALANI/HAVALİMANI': ('107000', 'HAVAYOLLARI', '107001'),
            'HELİKOPTER İNİŞ ALANI': ('107000', 'HAVAYOLLARI', '107002'),
            'CAMİ': ('108000', 'İBADET ALANLARI', '108001'),
            'KİLİSE': ('108000', 'İBADET ALANLARI', '108002'),
            'MESCİT': ('108000', 'İBADET ALANLARI', '108003'),
            'ŞAPEL': ('108000', 'İBADET ALANLARI', '108004'),
            'SİNAGOG (HAVRA)': ('108000', 'İBADET ALANLARI', '108005'),
            'BİSİKLET PARKI': ('109000', 'KARAYOLLARI', '109001'),
            'TERMİNAL (OTOGAR)': ('109000', 'KARAYOLLARI', '109002'),
            'GENEL OTOPARK ALANI': ('109000', 'KARAYOLLARI', '109003'),
            'TIR, KAMYON, MAKİNE PARKI VE GARAJ ALANI': ('109000', 'KARAYOLLARI', '109004'),
            'ASKERİ ALAN': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110001'),
            'AKARYAKIT VE SERVİS İSTASYONU ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110002'),
            'BETON SANTRALİ': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110003'),
            'BELEDİYE HİZMET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110004'),
            'DEPOLAMA ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110005'),
            'ENDÜSTRİYEL GELİŞME BÖLGESİ': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110006'),
            'İDARİ HİZMET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110007'),
            'İMALATHANE TESİS ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110008'),
            'TİCARET - KONUT ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110009'),
            'KÜÇÜK SANAYİ ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110010'),
            'LOJİSTİK TESİS ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110011'),
            'PAZAR ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110012'),
            'RESMİ KURUM ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110013'),
            'SANAYİ TESİS ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110014'),
            'SU ÜRÜNLERİ ÜRETİM VE YETİŞTİRME TESİSİ': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110015'),
            'TARIM VE HAYVANCILIK TESİS ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110016'),
            'TİCARET-TURİZM-KONUT ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110017'),
            'TİCARET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110018'),
            'T1 TİCARET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110019'),
            'T2 TİCARET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110020'),
            'T3 TİCARET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110021'),
            'TİCARET - TURİZM ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110022'),
            'TOPLU İŞYERLERİ': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110023'),
            'TOPTAN TİCARET ALANI': ('110000', 'KENTSEL ÇALIŞMA ALANLARI', '110024'),
            'HAVAİ HAT İSTASYONU': ('111000', 'KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', '111001'),
            'HAVARAY İSTASYONU': ('111000', 'KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', '111002'),
            'RAYLI TOPLU TAŞIMA İSTASYONU': ('111000', 'KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', '111003'),
            'TOPLU TAŞINIM TÜRLERİ ARASI DEĞİŞİM VE AKTARMA ALANI': ('111000', 'KENTSEL TOPLU TAŞIMA GÜZERGAHLARI', '111004'),
            'GELİŞME KONUT ALANI': ('112000', 'KONUT ALANLARI / YERLEŞİM ALANLARI', '112001'),
            'YERLEŞİK KONUT ALANI': ('112000', 'KONUT ALANLARI / YERLEŞİM ALANLARI', '112002'),
            '1. DERECE ARKEOLOJİK SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113001'),
            '1. DERECE DOĞAL SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113002'),
            '2. DERECE ARKEOLOJİK SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113003'),
            '2. DERECE DOĞAL SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113004'),
            '3. DERECE ARKEOLOJİK SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113005'),
            '3. DERECE DOĞAL SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113006'),
            'EKOLOJİK NİTELİĞİ KORUNACAK ALAN': ('113000', 'KORUNACAK ALANLAR', '113007'),
            'HASSAS ENDEMİK BİYOTOP ALANI': ('113000', 'KORUNACAK ALANLAR', '113008'),
            'KORUNMASI GEREKLİ FLORA VE FAUNA ALANI': ('113000', 'KORUNACAK ALANLAR', '113009'),
            'KENTSEL SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113010'),
            'KESİN KORUNACAK HASSAS ALAN': ('113000', 'KORUNACAK ALANLAR', '113011'),
            'NİTELİKLİ DOĞAL KORUMA ALANI': ('113000', 'KORUNACAK ALANLAR', '113012'),
            'ÖÇK BÖLGESİ HASSAS ALAN (A)': ('113000', 'KORUNACAK ALANLAR', '113013'),
            'ÖÇK BÖLGESİ HASSAS ALAN (B)': ('113000', 'KORUNACAK ALANLAR', '113014'),
            'ÖÇK BÖLGESİ HASSAS ALAN (C)': ('113000', 'KORUNACAK ALANLAR', '113015'),
            'ÖZEL ÇEVRE KORUMA BÖLGESİ (ÖÇK)': ('113000', 'KORUNACAK ALANLAR', '113016'),
            'SÜRDÜRÜLEBİLİR KORUMA VE KONTROLLÜ KULLANIM ALANI': ('113000', 'KORUNACAK ALANLAR', '113017'),
            'TABİATI KORUMA ALANI': ('113000', 'KORUNACAK ALANLAR', '113018'),
            'TARİHİ SİT ALANI': ('113000', 'KORUNACAK ALANLAR', '113019'),
            'ULUSLARARASI SÖZLEŞMELERLE BELİRLENEN KORUMA ALAN SINIRI': ('113000', 'KORUNACAK ALANLAR', '113020'),
            'YABAN HAYATI KORUMA VE GELİŞTİRME ALANI': ('113000', 'KORUNACAK ALANLAR', '113021'),
            'YÖRESEL MİMARİ ÖZELLİKLERİ KORUNACAK ALAN': ('113000', 'KORUNACAK ALANLAR', '113022'),
            'MİLLİ PARK': ('113000', 'KORUNACAK ALANLAR', '113023'),
            'TABİAT PARKI ALANI': ('113000', 'KORUNACAK ALANLAR', '113024'),
            'TESCİLLİ ANIT YAPI': ('113000', 'KORUNACAK ALANLAR', '113025'),
            'TESCİLLİ BİNA': ('113000', 'KORUNACAK ALANLAR', '113026'),
            'TESCİLLİ PARSEL': ('113000', 'KORUNACAK ALANLAR', '113027'),
            'TESCİLLİ TABİAT VARLIĞI': ('113000', 'KORUNACAK ALANLAR', '113028'),
            'ASKERİ YASAK VE GÜVENLİK BÖLGESİ': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114001'),
            'ENDÜSTRİ BÖLGESİ': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114002'),
            'ORGANİZE SANAYİ BÖLGESİ': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114003'),
            'SERBEST BÖLGE': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114004'),
            'TEKNOLOJİ GELİŞTİRME BÖLGESİ': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114005'),
            'AİLE SAĞLIĞI MERKEZİ': ('115000', 'SAĞLIK TESİSLERİ ALANI', '115001'),
            'HASTANE': ('115000', 'SAĞLIK TESİSLERİ ALANI', '115002'),
            'ÖZEL SAĞLIK TESİSİ ALANI': ('115000', 'SAĞLIK TESİSLERİ ALANI', '115003'),
            'SAĞLIK TESİSİ ALANI': ('115000', 'SAĞLIK TESİSLERİ ALANI', '115004'),
            'AÇIK SPOR TESİSİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116001'),
            'KAPALI SPOR TESİSİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116002'),
            'KONGRE VE SERGİ MERKEZİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116003'),
            'KREŞ, GÜNDÜZ BAKIMEVİ': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116004'),
            'KÜLTÜREL TESİS ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116005'),
            'ÖZEL AÇIK SPOR TESİSİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116006'),
            'ÖZEL KAPALI SPOR TESİSİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116007'),
            'ÖZEL KREŞ, GÜNDÜZ BAKIMEVİ': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116008'),
            'ÖZEL KÜLTÜREL TESİS ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116009'),
            'ÖZEL SOSYAL TESİS ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116011'),
            'ÖZEL YURT ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116012'),
            'ŞEFKAT EVLERİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116013'),
            'SOSYAL TESİS ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116014'),
            'YAŞLI BAKIMEVİ ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116015'),
            'YURT ALANI': ('116000', 'SOSYAL VE KÜLTÜREL TESİS ALANI', '116016'),
            'ATIKSU TESİSLERİ ALANI (ARITMA, TERFİ MERKEZİ)': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117001'),
            'İÇME SUYU TESİSLERİ ALANI (DEPOLAMA, ARITMA, TERFİ MERKEZİ)': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117002'),
            'KATI ATIK TESİSLERİ ALANI (BOŞALTMA, BERTARAF, İŞLEME, TRANSFER VE DEPOLAMA)': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117003'),
            'SU KAYNAKLARI TOPLAMA YERİ (KAPTAJ ALANI)': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117004'),
            'SU YÜZEYİ': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117005'),
            'TEHLİKELİ ATIK TESİSLERİ ALANI (BERTARAF VE DEPOLAMA)': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117006'),
            'TEKNİK ALTYAPI ALANI': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117007'),
            'YAPAY ADA': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117008'),
            'APART OTEL ALANI': ('118000', 'TURİZM ALANLARI', '118001'),
            'GOLF ALANI': ('118000', 'TURİZM ALANLARI', '118002'),
            'GÜNÜBİRLİK TESİS ALANI': ('118000', 'TURİZM ALANLARI', '118003'),
            'HOSTEL ALANI': ('118000', 'TURİZM ALANLARI', '118004'),
            'KAMPİNG ALANI': ('118000', 'TURİZM ALANLARI', '118005'),
            'KIŞ SPORLARI VE KAYAK TESİSİ ALANI': ('118000', 'TURİZM ALANLARI', '118006'),
            'MOTEL ALANI': ('118000', 'TURİZM ALANLARI', '118007'),
            'OTEL ALANI': ('118000', 'TURİZM ALANLARI', '118008'),
            'PANSİYON ALANI': ('118000', 'TURİZM ALANLARI', '118009'),
            'SAĞLIK ODAKLI TATİL KÖYÜ': ('118000', 'TURİZM ALANLARI', '118010'),
            'TATİL KÖYÜ ALANI': ('118000', 'TURİZM ALANLARI', '118011'),
            'TERMAL TURİZM ALANI': ('118000', 'TURİZM ALANLARI', '118012'),
            'BORU HATTI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119001'),
            'DEMİRYOLLARI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119002'),
            'ENERJİ NAKİL HATTI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119003'),
            'HAVA ALANI HAVA KORİDORU': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119004'),
            'HAVAALANI/HAVALİMANI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119005'),
            'İÇME SUYU ANA İLETİM HATTI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119006'),
            'JEOTERMAL KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119007'),
            'KARAYOLLARI YOL KENARI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119008'),
            'İÇME VE KULLANMA SUYU KISA MESAFELİ KORUMA ALANI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119009'),
            'İÇME VE KULLANMA SUYU MUTLAK KORUMA ALANI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119010'),
            'İÇME VE KULLANMA SUYU ORTA MESAFELİ KORUMA ALANI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119011'),
            'İÇME VE KULLANMA SUYU UZUN MESAFELİ KORUMA ALANI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119012'),
            'NÜKLEER ENERJİ ÜRETİM ALANI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119013'),
            'SAĞLIK KORUMA BANDI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119014'),
            'SU KANALLARI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119015'),
            'SULAK ALAN BÖLGESİ': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119016'),
            'SULAK ALAN EKOLOJİK ETKİLENME BÖLGESİ': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119017'),
            'SULAK ALAN MUTLAK KORUMA BÖLGESİ': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119018'),
            'SULAK ALAN ÖZEL HÜKÜM BÖLGESİ': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119019'),
            'SULAK ALAN TAMPON BÖLGESİ': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119020'),
            'YANICI PARLAYICI VE PATLAYICI MADDELER KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119021'),
            'YER ALTI SU KAYNAKLARI KORUMA KUŞAĞI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119022'),
            'YER ALTI SU KAYNAKLARI KORUMA ALANLARI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119023'),
            'SİT ETKİLEŞİM GEÇİŞ ALANI SINIRI': ('113000', 'KORUNACAK ALANLAR', '113101'),
            'TOPLU KONUT ALANI SINIRI': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114108'),
            'TURİZM MERKEZİ/KÜLTÜR VE TURİZM KORUMA VE GELİŞİM ALT BÖLGE SINIRI': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114109'),
            'SULAK ALAN SINIRI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119102'),
            'SAHİL ŞERİDİ': ('114000', 'ÖZEL KANUNLARLA BELİRLENEN ALAN VE SINIRLAR', '114200'),
            'GOLF TURİZMİ': ('118000', 'TURİZM ALANLARI', '118200'),
            'KATLI OTOPARK': ('109000', 'KARAYOLLARI', '109100'),
            'LİMAN': ('120000', 'DENİZYOLLARI', '120100'),
            'TÜNEL ETKİ ALANI': ('119000', 'YAPI SINIRLAMASI GETİRİLEREK KORUNACAK ALANLAR', '119200'),
            'ENERJİ DEPOLAMA ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106100'),
            'RAFİNERİ-PETROKİMYA TESİSİ ALANI': ('106000', 'ENERJI ÜRETİM DAĞITIM VE DEPOLAMA', '106200'),
            'ATIK GERİ KAZANIM TESİSLERİ ALANI': ('117000', 'SU - ATIKSU VE ATIK SİSTEMLERİ', '117100'),
            'EKOTURİZM/KIRSAL TURİZM': ('118000', 'TURİZM ALANLARI', '118201'),  
            'ELEKTRİKLİ ARAÇ ŞARJ İSTASYONU': ('109000', 'KARAYOLLARI', '109200'),
            'SOKAK HAYVANLARI BARINAĞI ALANI': ('123000', 'SOSYAL ALT YAPI ALANLARI', '123100')
        }

        stats = {}
        total_area = 0

        feedback.pushInfo("2. Mekansal alanlar hesaplanıyor...")
        for feature in clipped.getFeatures():
            fonksiyon_raw = feature['uipfonksiyon']
            fonksiyon = str(fonksiyon_raw).strip().upper() if fonksiyon_raw else ""
            
            geom = feature.geometry()
            alan = geom.area()

            if fonksiyon not in lookup:
                continue

            id1, grup, id2 = lookup[fonksiyon]
            key = (id1, grup, id2, fonksiyon)

            if key not in stats:
                stats[key] = {'adet': 0, 'alan': 0.0}

            stats[key]['adet'] += 1
            stats[key]['alan'] += alan
            total_area += alan

        fields = QgsFields()
        fields.append(QgsField('id1', QVariant.String))
        fields.append(QgsField('ust_konu_grup', QVariant.String))
        fields.append(QgsField('id2', QVariant.String))
        fields.append(QgsField('uip_fonksiyon', QVariant.String))
        fields.append(QgsField('adet', QVariant.Int))
        fields.append(QgsField('fonksiyon_toplam_alan_m2', QVariant.Double))
        fields.append(QgsField('m2_per_kisi', QVariant.Double))
        fields.append(QgsField('yuzde_plan', QVariant.Double))

        (sink, sink_id) = self.parameterAsSink(parameters, 'output', context, fields, QgsWkbTypes.NoGeometry, plan_layer.sourceCrs())

        feedback.pushInfo("3. Tablo çıktıları oluşturuluyor...")
        for key, data in stats.items():
            id1, grup, id2, fonksiyon = key
            alan_m2 = data['alan']
            
            m2_per_kisi = alan_m2 / plan_nufusu if plan_nufusu > 0 else 0
            yuzde = (alan_m2 / total_area) * 100 if total_area > 0 else 0

            f = QgsFeature(fields)
            f.setAttributes([
                id1, grup, id2, fonksiyon, data['adet'],
                round(alan_m2, 2), round(m2_per_kisi, 2), round(yuzde, 2)
            ])
            sink.addFeature(f, QgsFeatureSink.FastInsert)

        return {'output': sink_id}

    def name(self): return '6_uip_plan_kent_karakter_tablosu'
    def displayName(self): return '6. Plan Kent Karakter Tablosu (UİP)'
    def group(self): return 'UİP Plan Analiz Araçları'
    def groupId(self): return 'uip_plan_analiz_araclari'
    def createInstance(self): return PlanKentKarakterTablosuUIP()