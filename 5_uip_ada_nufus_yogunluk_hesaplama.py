# File: 5_uip_ada_nufus_yogunluk_hesaplama_v2.py
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsFeatureSink
)
import math

class YapiYogunluguVeNufusHesaplaUIP(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    FLAT_SIZE = 'FLAT_SIZE'
    HOUSEHOLD_SIZE = 'HOUSEHOLD_SIZE'
    KONUT_ORANI = 'KONUT_ORANI'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 'UİP Ada Katmanı (uipfonksiyon, emsal/kaks içermeli)', [QgsProcessing.TypeVectorPolygon]
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.FLAT_SIZE, 'Ortalama Daire Büyüklüğü (m²)', type=QgsProcessingParameterNumber.Double, defaultValue=120.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.HOUSEHOLD_SIZE, 'Ortalama Hane Halkı Büyüklüğü', type=QgsProcessingParameterNumber.Double, defaultValue=2.77
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.KONUT_ORANI, 'Karma Kullanım Konut Oranı (%)', type=QgsProcessingParameterNumber.Double, defaultValue=30.0, minValue=0.0, maxValue=100.0
        ))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'Analitik Nüfus ve Yoğunluk Katmanı'))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        avg_flat = self.parameterAsDouble(parameters, self.FLAT_SIZE, context)
        avg_hh = self.parameterAsDouble(parameters, self.HOUSEHOLD_SIZE, context)
        konut_orani = self.parameterAsDouble(parameters, self.KONUT_ORANI, context) / 100.0

        fields = QgsFields(source.fields())
        new_fields = [
            QgsField("kaks_or_emsal", QVariant.Double),
            QgsField("Toplam_Insaat_Alani", QVariant.Double),
            QgsField("Tahmini_Nufus", QVariant.Double),
            QgsField("Kisi_Basina_TIA", QVariant.Double),
            QgsField("Nufus_Yogunlugu_m2", QVariant.Double),
            QgsField("Yogunluk_Sinifi", QVariant.String),
            QgsField("Z_Skoru", QVariant.Double)
        ]
        
        for fld in new_fields:
            if fields.indexOf(fld.name()) == -1:
                fields.append(fld)

        field_names = [f.name() for f in source.fields()]
        
        kisi_basina_tia_list = []
        nufus_yogunlugu_list = []
        processed_data = []

        for feat in source.getFeatures():
            uip_raw = feat.attribute("uipfonksiyon")
            uip = str(uip_raw).strip().upper() if uip_raw else ""

            emsal_val = None
            kaks_val = None
            
            if "emsal" in field_names and feat["emsal"]:
                try: emsal_val = float(str(feat["emsal"]).replace(",", "."))
                except ValueError: pass
            
            if "kaks" in field_names and feat["kaks"]:
                try: kaks_val = float(str(feat["kaks"]).replace(",", "."))
                except ValueError: pass

            kullanilan_emsal = None
            if emsal_val is not None and kaks_val is not None:
                kullanilan_emsal = emsal_val if abs(emsal_val - 1.6) < abs(kaks_val - 1.6) else kaks_val
            else:
                kullanilan_emsal = emsal_val if emsal_val is not None else kaks_val

            if kullanilan_emsal is None:
                continue

            area = feat.geometry().area()
            tia = round(kullanilan_emsal * area, 2)
            
            tahmini_nufus = (tia / avg_flat) * avg_hh

            if any(x in uip for x in ['YERLEŞİK KONUT ALANI', 'GELİŞME KONUT ALANI']):
                pass
            elif any(x in uip for x in ['TİCARET-TURİZM-KONUT ALANI', 'TİCARET - KONUT ALANI']):
                tahmini_nufus *= konut_orani
            else:
                tahmini_nufus = 0.0

            tahmini_nufus = round(tahmini_nufus, 2)
            
            kisi_basina_tia = round(tia / tahmini_nufus, 2) if tahmini_nufus > 0 else 0.0
            # Net nüfus yoğunluğu (Kişi / m2) olarak hesaplanır ve virgülden sonra 4 basamak alınır
            nufus_yogunlugu_m2 = round(tahmini_nufus / area, 4) if area > 0 else 0.0

            if tahmini_nufus > 0:
                kisi_basina_tia_list.append(kisi_basina_tia)
                nufus_yogunlugu_list.append(nufus_yogunlugu_m2)

            processed_data.append({
                'feat': feat,
                'kullanilan_emsal': kullanilan_emsal,
                'tia': tia,
                'tahmini_nufus': tahmini_nufus,
                'kisi_basina_tia': kisi_basina_tia,
                'nufus_yogunlugu_m2': nufus_yogunlugu_m2
            })

        lower_bound, upper_bound = 0, 0
        mean_density, std_dev_density = 0, 0

        if kisi_basina_tia_list:
            sorted_tia = sorted(kisi_basina_tia_list)
            n = len(sorted_tia)
            q1 = sorted_tia[int(n * 0.25)]
            q3 = sorted_tia[int(n * 0.75)]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

        if nufus_yogunlugu_list:
            mean_density = sum(nufus_yogunlugu_list) / len(nufus_yogunlugu_list)
            variance = sum((x - mean_density) ** 2 for x in nufus_yogunlugu_list) / len(nufus_yogunlugu_list)
            std_dev_density = math.sqrt(variance)

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, fields, QgsWkbTypes.Polygon, source.sourceCrs())

        for data in processed_data:
            out_feat = QgsFeature(fields)
            out_feat.setGeometry(data['feat'].geometry())
            
            for i in range(len(field_names)):
                out_feat.setAttribute(i, data['feat'].attribute(i))
            
            kisi_basina_tia = data['kisi_basina_tia']
            nufus_yogunlugu_m2 = data['nufus_yogunlugu_m2']

            yogunluk_sinifi = "Nüfus Yok"
            z_score = 0.0

            if data['tahmini_nufus'] > 0:
                if kisi_basina_tia < lower_bound: yogunluk_sinifi = "Kritik Düşük (Sıkışık)"
                elif kisi_basina_tia > upper_bound: yogunluk_sinifi = "Kritik Yüksek (Seyrek)"
                else: yogunluk_sinifi = "Normal Dağılım"

                if std_dev_density > 0:
                    z_score = round((nufus_yogunlugu_m2 - mean_density) / std_dev_density, 3)

            out_feat.setAttribute("kaks_or_emsal", data['kullanilan_emsal'])
            out_feat.setAttribute("Toplam_Insaat_Alani", data['tia'])
            out_feat.setAttribute("Tahmini_Nufus", data['tahmini_nufus'])
            out_feat.setAttribute("Kisi_Basina_TIA", kisi_basina_tia)
            out_feat.setAttribute("Nufus_Yogunlugu_m2", nufus_yogunlugu_m2)
            out_feat.setAttribute("Yogunluk_Sinifi", yogunluk_sinifi)
            out_feat.setAttribute("Z_Skoru", z_score)

            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)

        return {self.OUTPUT: dest_id}

    def name(self): return '5_uip_ada_nufus_yogunluk_hesaplama'
    def displayName(self): return '5. Ada Net Nüfus ve Analitik Yoğunluk Hesaplama (1/1000 UİP)'
    def group(self): return 'UİP Kentsel Hesaplamalar'
    def groupId(self): return 'uip_kentsel_hesaplamalar'
    def createInstance(self): return YapiYogunluguVeNufusHesaplaUIP()