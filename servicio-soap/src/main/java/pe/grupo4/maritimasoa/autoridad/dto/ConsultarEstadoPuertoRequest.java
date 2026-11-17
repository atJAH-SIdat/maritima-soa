package pe.grupo4.maritimasoa.autoridad.dto;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlElement;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "consultarEstadoPuertoRequest")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "", propOrder = { "codigoPuerto", "fechaZarpe" })
public class ConsultarEstadoPuertoRequest {

	@XmlElement(required = true)
	private String codigoPuerto;

	/** Fecha en formato AAAA-MM-DD. */
	@XmlElement(required = true)
	private String fechaZarpe;

	public String getCodigoPuerto() {
		return codigoPuerto;
	}

	public void setCodigoPuerto(String codigoPuerto) {
		this.codigoPuerto = codigoPuerto;
	}

	public String getFechaZarpe() {
		return fechaZarpe;
	}

	public void setFechaZarpe(String fechaZarpe) {
		this.fechaZarpe = fechaZarpe;
	}
}
