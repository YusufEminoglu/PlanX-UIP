# File: 8_uip_duzenleme_ortaklik_payi.py
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

class DuzenlemeOrtaklikPayiUIP(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('plan_onama_siniri', 'Plan Onama Sınırı (Poligon)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterVectorLayer('plan_katmani', 'UİP Plan Katmanı (Fonksiyonlar)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterNumber('plan_nufusu', 'Plan Nüfusu', QgsProcessingParameterNumber.Double, minValue=1.0))
        self.addParameter(QgsProcessingParameterFeatureSink('duzenleme_ortaklik_tablosu', 'Çıktı 1: DOP Esas Tablosu', type=QgsProcessing.TypeVector))
        self.addParameter(QgsProcessingParameterFeatureSink('dop_tablosu', 'Çıktı 2: DOP Oranı Tablosu', type=QgsProcessing.TypeVector))

    def processAlgorithm(self, parameters, context, feedback):
        sinir_layer = self.parameterAsVectorLayer(parameters, 'plan_onama_siniri', context)
        plan_layer = self.parameterAsVectorLayer(parameters, 'plan_katmani', context)
        plan_nufus = self.parameterAsDouble(parameters, 'plan_nufusu', context)

        # Onama sınırı toplam alanı
        plan_alani_m2 = sum(f.geometry().area() for f in sinir_layer.getFeatures() if f.geometry())

        feedback.pushInfo("Plan katmanı sınır üzerinden kesiliyor...")
        clipped_result = processing.run(
            'native:clip',
            {'INPUT': plan_layer.source(), 'OVERLAY': sinir_layer.source(), 'OUTPUT': 'TEMPORARY_OUTPUT'},
            context=context, feedback=feedback, is_child_algorithm=True
        )
        clipped_id = clipped_result['OUTPUT']
        clipped_layer = QgsProcessingUtils.mapLayerFromString(clipped_id, context)

        ozel_fonksiyonlar = {
            'TİCARET - KONUT ALANI', 'TİCARET-TURİZM-KONUT ALANI', 'GELİŞME KONUT ALANI',
            'YERLEŞİK KONUT ALANI', 'TİCARET ALANI', 'T1 TİCARET ALANI', 'T2 TİCARET ALANI',
            'T3 TİCARET ALANI', 'TOPTAN TİCARET ALANI', 'TOPLU İŞYERLERİ', 'ÖZEL ANAOKULU ALANI',
            'ÖZEL EĞİTİM ALANI', 'ÖZEL SAĞLIK TESİSİ ALANI', 'ÖZEL AÇIK SPOR TESİSİ ALANI',
            'ÖZEL KAPALI SPOR TESİSİ ALANI', 'ÖZEL KREŞ, GÜNDÜZ BAKIMEVİ', 'ÖZEL KÜLTÜREL TESİS ALANI',
            'ÖZEL SOSYAL TESİS ALANI', 'ÖZEL YURT ALANI'
        }

        stats = {}
        toplam_alan = 0
        ozel_alan = 0

        for feat in clipped_layer.getFeatures():
            fonk_raw = feat['uipfonksiyon']
            fonk = str(fonk_raw).strip().upper() if fonk_raw else ""
            
            alan = feat.geometry().area()
            toplam_alan += alan

            if fonk in ozel_fonksiyonlar:
                ozel_alan += alan

            if fonk not in stats:
                stats[fonk] = {'alan': 0.0, 'adet': 0}
            stats[fonk]['alan'] += alan
            stats[fonk]['adet'] += 1

        # Tablo 1: DOP Esas Tablosu
        tablo1_fields = QgsFields()
        tablo1_fields.append(QgsField('uip_fonksiyon', QVariant.String))
        tablo1_fields.append(QgsField('adet', QVariant.Int))
        tablo1_fields.append(QgsField('fonksiyon_toplam_alan_m2', QVariant.Double))
        tablo1_fields.append(QgsField('m2_per_kisi', QVariant.Double))
        tablo1_fields.append(QgsField('yuzde_plan', QVariant.Double))

        (sink1, dest_id1) = self.parameterAsSink(parameters, 'duzenleme_ortaklik_tablosu', context, tablo1_fields, QgsWkbTypes.NoGeometry, plan_layer.sourceCrs())

        for fonk, data in stats.items():
            alan = data['alan']
            f = QgsFeature(tablo1_fields)
            f.setAttributes([
                fonk, data['adet'], round(alan, 2),
                round(alan / plan_nufus, 2) if plan_nufus > 0 else 0,
                round((alan / plan_alani_m2) * 100, 2) if plan_alani_m2 > 0 else 0
            ])
            sink1.addFeature(f, QgsFeatureSink.FastInsert)

        # Tablo 2: DOP Oranı Hesabı
        yol_alan = plan_alani_m2 - toplam_alan
        kamu_alan = (toplam_alan - ozel_alan) + yol_alan
        dop_oran = (kamu_alan / plan_alani_m2) * 100 if plan_alani_m2 > 0 else 0

        tablo2_fields = QgsFields()
        tablo2_fields.append(QgsField('yol_alan_m2', QVariant.Double))
        tablo2_fields.append(QgsField('kamu_toplam_alan_m2', QVariant.Double))
        tablo2_fields.append(QgsField('ozel_toplam_alan_m2', QVariant.Double))
        tablo2_fields.append(QgsField('dop_oran', QVariant.Double))

        (sink2, dest_id2) = self.parameterAsSink(parameters, 'dop_tablosu', context, tablo2_fields, QgsWkbTypes.NoGeometry, plan_layer.sourceCrs())

        f2 = QgsFeature(tablo2_fields)
        f2.setAttributes([round(yol_alan, 2), round(kamu_alan, 2), round(ozel_alan, 2), round(dop_oran, 2)])
        sink2.addFeature(f2, QgsFeatureSink.FastInsert)

        return {
            'duzenleme_ortaklik_tablosu': dest_id1,
            'dop_tablosu': dest_id2
        }

    def name(self): return '8_uip_duzenleme_ortaklik_payi'
    def displayName(self): return '8. Düzenleme Ortaklık Payı (DOP) Hesabı (UİP)'
    def group(self): return 'UİP Plan Analiz Araçları'
    def groupId(self): return 'uip_plan_analiz_araclari'
    def createInstance(self): return DuzenlemeOrtaklikPayiUIP()