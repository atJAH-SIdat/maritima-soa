package pe.grupo4.maritimasoa.autoridad.dto;

import jakarta.xml.bind.annotation.XmlAccessType;
import jakarta.xml.bind.annotation.XmlAccessorType;
import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;

@XmlRootElement(name = "consultarEstadoPuertoResponse")
@XmlAccessorType(XmlAccessType.FIELD)
@XmlType(name = "", propOrder = { "puertoAbierto", "condicionMaritima", "codigoAutorizacionZarpe" })
public class ConsultarEstadoPuertoResponse {

	private boolean puertoAbierto;
	private String condicionMaritima;
	/** Solo se informa cuando el puerto está abierto. */
	private String codigoAutorizacionZarpe;

	public ConsultarEstadoPuertoResponse() {
	}

	public ConsultarEstadoPuertoResponse(boolean puertoAbierto, String condicionMaritima,
			String codigoAutorizacionZarpe) {
		this.puertoAbierto = puertoAbierto;
		this.condicionMaritima = condicionMaritima;
		this.codigoAutorizacionZarpe = codigoAutorizacionZarpe;
	}

	public boolean isPuertoAbierto() {
		return puertoAbierto;
	}

	public String getCondicionMaritima() {
		return condicionMaritima;
	}

	public String getCodigoAutorizacionZarpe() {
		return codigoAutorizacionZarpe;
	}
}
