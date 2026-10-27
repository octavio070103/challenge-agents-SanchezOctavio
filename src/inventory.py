"""Módulo para la carga y gestión del inventario fijo de equipos."""

import json
from pathlib import Path
from typing import List, Set, Union
from src.models import Unidad


DEFAULT_INVENTORY_PATH = Path("data") / "inventory.json"


def cargar_inventario(inventory_path: Union[str, Path] = DEFAULT_INVENTORY_PATH) -> List[Unidad]:
    """
    Carga el inventario de equipos desde el archivo JSON especificado.
    
    Args:
        inventory_path: Ruta al archivo JSON de inventario.
        
    Returns:
        Lista de objetos Unidad.
    """
    path = Path(inventory_path)
    if not path.is_file():
        # Si la ruta no existe relativa al cwd actual, buscar relativa a la raíz del proyecto
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / inventory_path

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Unidad(id=item["id"], name=item["name"]) for item in data]


def obtener_catalogo_ids(inventory_path: Union[str, Path] = DEFAULT_INVENTORY_PATH) -> Set[str]:
    """Retorna el conjunto de IDs válidos del inventario."""
    unidades = cargar_inventario(inventory_path)
    return {u.id for u in unidades}
