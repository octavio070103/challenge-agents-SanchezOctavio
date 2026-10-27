"""Excepciones de dominio para el sistema de reservas."""


class ReservaError(Exception):
    """Excepción base para todos los errores del sistema de reservas."""
    pass


class ValidationError(ReservaError, ValueError):
    """Excepción para errores de validación de entradas."""
    pass


class UnidadNoEncontradaError(ValidationError):
    """Lanzada cuando la unidad no existe en el catálogo fijo."""
    pass


class SolicitanteInvalidoError(ValidationError):
    """Lanzada cuando el solicitante es vacío, inválido o sólo espacios."""
    pass


class HorarioInvalidoError(ValidationError):
    """Lanzada cuando la fecha de inicio es igual o posterior a la fecha de fin."""
    pass


class SuperposicionError(ReservaError):
    """Lanzada cuando se intenta reservar un horario superpuesto con otra reserva activa."""
    pass


class ReservaNotFoundError(ReservaError, KeyError):
    """Lanzada cuando se busca o cancela una reserva inexistente."""
    pass
