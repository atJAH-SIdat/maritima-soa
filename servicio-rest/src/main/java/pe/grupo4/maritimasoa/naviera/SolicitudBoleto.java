package pe.grupo4.maritimasoa.naviera;

/** Cuerpo JSON de POST /api/boletos. */
public record SolicitudBoleto(
		String codigoViaje,
		String documentoPasajero,
		String nombrePasajero,
		String tipoRuta,
		Integer cantidadAsientos,
		String codigoAutorizacionZarpe) {
}
