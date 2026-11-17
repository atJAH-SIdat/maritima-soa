package pe.grupo4.maritimasoa.naviera;

import java.time.LocalDate;

/** Viaje programado por la naviera. tipoRuta es NACIONAL o INTERNACIONAL. */
public record Viaje(
		String codigoViaje,
		String origen,
		String destino,
		String paisDestino,
		String tipoRuta,
		String codigoPuerto,
		LocalDate fechaZarpe,
		int cuposDisponibles,
		double precioUnitario) {

	public Viaje conCupos(int nuevosCupos) {
		return new Viaje(codigoViaje, origen, destino, paisDestino, tipoRuta, codigoPuerto, fechaZarpe,
				nuevosCupos, precioUnitario);
	}
}
