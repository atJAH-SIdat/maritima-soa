package pe.grupo4.maritimasoa.autoridad;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.ws.wsdl.wsdl11.DefaultWsdl11Definition;
import org.springframework.xml.xsd.SimpleXsdSchema;
import org.springframework.xml.xsd.XsdSchema;

/** Publica el WSDL en http://localhost:8083/ws/autoridadPortuaria.wsdl, generado a partir del XSD. */
@Configuration
public class WebServiceConfig {

	public static final String NAMESPACE = "http://maritimasoa.grupo4.pe/autoridadportuaria";

	// El nombre del bean define el nombre del archivo WSDL.
	@Bean(name = "autoridadPortuaria")
	public DefaultWsdl11Definition autoridadPortuariaWsdl(XsdSchema autoridadPortuariaSchema) {
		DefaultWsdl11Definition wsdl = new DefaultWsdl11Definition();
		wsdl.setPortTypeName("AutoridadPortuariaPort");
		wsdl.setServiceName("AutoridadPortuariaService");
		wsdl.setLocationUri("/ws");
		wsdl.setTargetNamespace(NAMESPACE);
		wsdl.setSchema(autoridadPortuariaSchema);
		return wsdl;
	}

	@Bean
	public XsdSchema autoridadPortuariaSchema() {
		return new SimpleXsdSchema(new ClassPathResource("xsd/autoridad-portuaria.xsd"));
	}
}
