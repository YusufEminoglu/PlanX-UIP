# File: 1_uip_yol_platform_uretme.py
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsWkbTypes,
    QgsFeatureSink,
    QgsProcessing
)

class GenerateYolPlatformUIP(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 
            'Yol Orta Çizgi Katmanı (1000 UİP)', 
            [QgsProcessing.TypeVectorLine]
        ))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 
            'Yol Platform Katmanı (UİP)'
        ))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)

        fields = QgsFields()
        fields.append(QgsField("source_fid", QVariant.LongLong))
        fields.append(QgsField("yolTipi", QVariant.String))
        fields.append(QgsField("type", QVariant.String))     
        fields.append(QgsField("side", QVariant.String))     

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields, 
            QgsWkbTypes.MultiLineString, source.sourceCrs()
        )

        def offset_geometry(geom: QgsGeometry, offset: float) -> QgsGeometry:
            return geom.offsetCurve(offset, 8, QgsGeometry.JoinStyleRound, 2.0)

        total_features = source.featureCount() if source.featureCount() > 0 else 0
        current_feat = 0

        for feat in source.getFeatures():
            if feedback.isCanceled(): break
            
            try: fid = feat["fid"]
            except KeyError: fid = feat.id()

            try:
                yol_tipi = str(feat["yolTipi"]).strip().upper()
                refuj = float(feat["refujGenislik"] or 0.0)
                kaldirim = float(feat["kaldirimGenislik"] or 0.0)
                yol_genislik2 = float(feat["yolGenislik2"] or 0.0)
            except (KeyError, ValueError) as e:
                feedback.reportError(f"Veri okuma hatası (ID: {fid}): {e}")
                continue

            if yol_tipi == "BİSİKLET YOLU":
                continue

            geom: QgsGeometry = feat.geometry()

            # CENTER
            c_feat = QgsFeature(fields)
            c_feat.setAttribute("source_fid", fid)
            c_feat.setAttribute("yolTipi", yol_tipi)
            c_feat.setAttribute("type", "center")
            c_feat.setAttribute("side", "none")
            c_feat.setGeometry(geom)
            sink.addFeature(c_feat, QgsFeatureSink.FastInsert)

            # REFÜJ
            if refuj > 0:
                for side, direction in [("left", -1), ("right", 1)]:
                    ref_geom = offset_geometry(geom, direction * (refuj / 2.0))
                    if ref_geom and not ref_geom.isEmpty():
                        f = QgsFeature(fields)
                        f.setAttributes([fid, yol_tipi, "refuj", side])
                        f.setGeometry(ref_geom)
                        sink.addFeature(f, QgsFeatureSink.FastInsert)

            # KALDIRIM (DIŞ VE İÇ)
            for side, direction in [("left", -1), ("right", 1)]:
                outer_offset = direction * (yol_genislik2 / 2.0)
                outer_geom = offset_geometry(geom, outer_offset)

                if outer_geom and not outer_geom.isEmpty():
                    f_out = QgsFeature(fields)
                    f_out.setAttributes([fid, yol_tipi, "kaldirim", f"{side}_outer"])
                    f_out.setGeometry(outer_geom)
                    sink.addFeature(f_out, QgsFeatureSink.FastInsert)

                if yol_tipi != "YAYA YOLU VE BÖLGESİ":
                    inner_offset = outer_offset + (direction * -1 * kaldirim)
                    inner_geom = offset_geometry(geom, inner_offset)

                    if inner_geom and not inner_geom.isEmpty():
                        f_in = QgsFeature(fields)
                        f_in.setAttributes([fid, yol_tipi, "kaldirim", f"{side}_inner"])
                        f_in.setGeometry(inner_geom)
                        sink.addFeature(f_in, QgsFeatureSink.FastInsert)

            current_feat += 1
            if total_features > 0: feedback.setProgress(int(current_feat / total_features * 100))

        return {self.OUTPUT: dest_id}

    def name(self): return '1_uip_yol_platform_uretme'
    def displayName(self): return '1. Yol Platformu Oluştur (1/1000 UİP)'
    def group(self): return 'UİP Yol İşlemleri'
    def groupId(self): return 'uip_yol_islemleri'
    def createInstance(self): return GenerateYolPlatformUIP()