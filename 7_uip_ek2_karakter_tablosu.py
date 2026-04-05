# File: 7_uip_ek2_karakter_tablosu.py
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
    QgsFeatureSink
)
from qgis.PyQt.QtCore import QVariant

class Ek2KarakterTablosuUIP(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('plan_katmani', 'UİP Plan Katmanı (Fonksiyonlar)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterVectorLayer('plan_onama_siniri', 'Plan Onama Sınırı (Poligon)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterNumber('plan_nufusu', 'Plan Nüfusu', QgsProcessingParameterNumber.Double, minValue=1.0))
        self.addParameter(QgsProcessingParameterVectorLayer('ek2_referans_tablosu', 'EK2 Referans Katmanı (GeoJSON/CSV)', [QgsProcessing.TypeVector]))
        self.addParameter(QgsProcessingParameterFeatureSink('output', 'Çıktı: 7. EK-2 Kent Karakter Tablosu', type=QgsProcessing.TypeVector))

    def processAlgorithm(self, parameters, context, feedback):
        plan_layer = self.parameterAsVectorLayer(parameters, 'plan_katmani', context)
        sinir_layer = self.parameterAsVectorLayer(parameters, 'plan_onama_siniri', context)
        nufus = self.parameterAsDouble(parameters, 'plan_nufusu', context)
        lookup_layer = self.parameterAsVectorLayer(parameters, 'ek2_referans_tablosu', context)

        lookup_fields = {field.name(): i for i, field in enumerate(lookup_layer.fields())}
        ek2_lookup = [f.attributes() for f in lookup_layer.getFeatures()]

        # Çoklu poligon olma ihtimaline karşı toplam plan alanını toplayarak hesapla
        onama_alani = sum(f.geometry().area() for f in sinir_layer.getFeatures() if f.geometry())

        grouped = {}
        for f in plan_layer.getFeatures():
            fonk_raw = f['uipfonksiyon']
            fonk_ad = str(fonk_raw).strip().upper() if fonk_raw else ""
            area = f.geometry().area()
            
            if fonk_ad not in grouped:
                grouped[fonk_ad] = {'alan': 0, 'adet': 0}
            grouped[fonk_ad]['alan'] += area
            grouped[fonk_ad]['adet'] += 1

        fields = QgsFields()
        columns = [
            ('grup_id', QVariant.String), ('grup_ad', QVariant.String),
            ('gosterge_id', QVariant.String), ('gosterge_ad', QVariant.String),
            ('fonk_id', QVariant.String), ('fonk_ad', QVariant.String),
            ('ek2_m2pkisi', QVariant.Double), ('gercek_m2pkisi', QVariant.Double),
            ('fark_m2pkisi', QVariant.Double), ('ek2_alan', QVariant.Double),
            ('gercek_alan', QVariant.Double), ('fark_alan', QVariant.Double),
            ('alan_orani', QVariant.Double), ('adet', QVariant.Int),
            ('yeterli_say', QVariant.Int), ('yetersiz_say', QVariant.Int),
            ('m2pkisi_yeterlilik', QVariant.String), ('alan_yeterlilik', QVariant.String)
        ]
        for col_name, qtype in columns:
            fields.append(QgsField(col_name, qtype))

        (sink, sink_id) = self.parameterAsSink(parameters, 'output', context, fields, QgsWkbTypes.NoGeometry, plan_layer.sourceCrs())

        for row in ek2_lookup:
            fonk_raw = row[lookup_fields['fonk_ad']]
            fonk_ad = str(fonk_raw).strip().upper() if fonk_raw else ""
            
            if fonk_ad not in grouped:
                continue

            min_area_type = row[lookup_fields['min_area_per_unit_calculation_type']]

            # EK-2 Nüfus aralığı metrikleri
            if nufus <= 75000:
                ek2_m2pkisi = float(row[lookup_fields['m2/person_if_pop_between_1-75000']] or 0)
            elif nufus <= 150000:
                ek2_m2pkisi = float(row[lookup_fields['m2/person_if_pop_between_75001_150000']] or 0)
            else:
                ek2_m2pkisi = float(row[lookup_fields['m2/person_if_pop_between_150001-500000']] or 0)

            gercek_alan = grouped[fonk_ad]['alan']
            adet = grouped[fonk_ad]['adet']
            gercek_m2pkisi = gercek_alan / nufus if nufus > 0 else 0
            fark_m2pkisi = gercek_m2pkisi - ek2_m2pkisi
            ek2_alan = nufus * ek2_m2pkisi
            fark_alan = gercek_alan - ek2_alan
            alan_orani = (gercek_alan / onama_alani) * 100 if onama_alani > 0 else 0

            if min_area_type == 'no_constraint':
                yeterli_say, yetersiz_say = adet, 0
            else:
                yeterli_say = 1 if gercek_m2pkisi >= ek2_m2pkisi else 0
                yetersiz_say = adet - yeterli_say

            m2pkisi_yeterlilik = 'Yeterli' if gercek_m2pkisi >= ek2_m2pkisi else 'Yetersiz'
            alan_yeterlilik = 'Yeterli' if gercek_alan >= ek2_alan else 'Yetersiz'

            feat = QgsFeature(fields)
            feat.setAttributes([
                row[lookup_fields['grup_id']], row[lookup_fields['grup_Ad']],
                row[lookup_fields['gosterge_id']], row[lookup_fields['gosterge_Ad']],
                row[lookup_fields['fonk_id']], fonk_ad,
                round(ek2_m2pkisi, 2), round(gercek_m2pkisi, 2), round(fark_m2pkisi, 2),
                round(ek2_alan, 2), round(gercek_alan, 2), round(fark_alan, 2),
                round(alan_orani, 2), adet, yeterli_say, yetersiz_say,
                m2pkisi_yeterlilik, alan_yeterlilik
            ])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)

        return {'output': sink_id}

    def name(self): return '7_uip_ek2_karakter_tablosu'
    def displayName(self): return '7. Fonksiyon Düzeyinde EK-2 Tablosu (UİP)'
    def group(self): return 'UİP Plan Analiz Araçları'
    def groupId(self): return 'uip_plan_analiz_araclari'
    def createInstance(self): return Ek2KarakterTablosuUIP()