# PlanX UIP Toolset

**An 8-stage automated workflow for Uygulama İmar Planı (Master Plan) production in QGIS — part of the PlanX suite**

PlanX UIP Toolset automates the implementation processes of 1/1000-scale Master Plans (Uygulama İmar Planı). Built with a vision of urban resilience and optimization-based planning, it generates road platforms, intersection trims, facade segmentations, population density calculations, and regulatory compliance tables through a sequential processing pipeline.

---

## Features

### 8-Stage Sequential Workflow

| # | Tool | Description |
|---|---|---|
| 1 | **Road Platform Generator** | Produces road platform polygons from centerlines |
| 2 | **Junction Trim** | Cleans intersection areas and trims overlapping road polygons |
| 3 | **Road Polygon Area Connector** | Links road polygonalization areas to the network |
| 4 | **Facade Segmentation** | Segments parcel facades and classifies frontages |
| 5 | **Block Population Density** | Calculates population density per block |
| 6 | **Urban Character Table** | Generates plan character (kentsel karakter) summary tables |
| 7 | **EK-2 Character Table** | Produces the regulatory EK-2 character table |
| 8 | **Düzenleme Ortaklık Payı (DOP)** | Computes land readjustment share ratios |

### Smart Post-Processing
- Automatically assigns QML styles to produced layers after Junction Trim and Facade Segmentation steps

### User Interface
- Hierarchical, icon-supported layout in the QGIS Processing Toolbox

## Installation

1. Download the latest `.zip` from [Releases](https://github.com/YusufEminoglu/PlanX-UIP/releases).
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Activate **PlanX UIP Toolset** from the plugin list.
4. Find the tools under **Processing Toolbox → PlanX UIP Toolset**.

## Compatibility

| Requirement | Value |
|---|---|
| QGIS minimum | 3.0 |
| License | GPL-3.0 |
| Status | Experimental |

## Author

**Yusuf Eminoglu** — Dokuz Eylül University, Department of City and Regional Planning  
[GitHub](https://github.com/YusufEminoglu) | yusuf.eminoglu@deu.edu.tr

Part of the **[PlanX](https://github.com/YusufEminoglu/PlanX)** urban planning plugin suite.
