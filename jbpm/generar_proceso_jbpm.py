"""Genera el proceso BPMN ejecutable en jBPM 7 (Business Central) para MaritimaSOA.

Uso: python generar_proceso_jbpm.py venta-pasajes-maritimos.bpmn
"""
import sys, os
from xml.sax.saxutils import escape

PROC_ID = "maritima-soa.venta-pasajes-maritimos"
PKG = "com.myspace.maritima_soa"

VARS = [
    ("codigoViaje", "String"), ("cantidadAsientos", "Integer"), ("documentoPasajero", "String"),
    ("nombrePasajero", "String"), ("numeroPasaporte", "String"), ("tipoRuta", "String"),
    ("codigoPuerto", "String"), ("fechaZarpe", "String"), ("paisDestino", "String"),
    ("cuposDisponibles", "Integer"), ("puertoAbierto", "Boolean"), ("codigoAutorizacionZarpe", "String"),
    ("habilitadoViaje", "Boolean"), ("idBoleto", "String"), ("montoTotal", "String"),
    ("muelleEmbarque", "String"), ("paseEmbarque", "String"), ("avisoEmbarque", "String"),
    ("estado", "String"), ("motivoRechazo", "String"),
]
VTYPE = dict(VARS)

# ---------- código Java de las tareas (Java 8: jBPM corre sobre JDK 8) ----------
HTTP_HELPER = r'''
  int code = con.getResponseCode();
  java.io.InputStream in = code < 400 ? con.getInputStream() : con.getErrorStream();
  String body = "";
  if (in != null) {
    java.util.Scanner sc = new java.util.Scanner(in, "UTF-8").useDelimiter("\\A");
    body = sc.hasNext() ? sc.next() : "";
    sc.close();
  }
'''

def campo_json(var, nombre, numero=False):
    patron = r'\"%s\"\\s*:\\s*(-?[0-9.]+)' % nombre if numero else r'\"%s\"\\s*:\\s*\"([^\"]*)\"' % nombre
    return f'java.util.regex.Matcher {var} = java.util.regex.Pattern.compile("{patron}").matcher(body);\n'

def campo_xml(var, nombre):
    return f'java.util.regex.Matcher {var} = java.util.regex.Pattern.compile("<(?:\\\\w+:)?{nombre}>([^<]*)<").matcher(body);\n'

SOAP_ENV = ('"<soapenv:Envelope xmlns:soapenv=\\"http://schemas.xmlsoap.org/soap/envelope/\\" '
            'xmlns:aut=\\"http://maritimasoa.grupo4.pe/autoridadportuaria\\"><soapenv:Body>"')
SOAP_END = '"</soapenv:Body></soapenv:Envelope>"'

def post_soap(cuerpo_expr):
    return f'''String url = "http://localhost:8083/ws";
try {{
  String xml = {SOAP_ENV} + {cuerpo_expr} + {SOAP_END};
  java.net.HttpURLConnection con = (java.net.HttpURLConnection) new java.net.URL(url).openConnection();
  con.setRequestMethod("POST");
  con.setDoOutput(true);
  con.setRequestProperty("Content-Type", "text/xml; charset=UTF-8");
  java.io.OutputStream out = con.getOutputStream();
  out.write(xml.getBytes("UTF-8"));
  out.close();
{HTTP_HELPER}'''

SCRIPTS = {}

SCRIPTS["T2"] = r'''// Consulta el viaje en NavieraReservasAPI (REST :8082)
String url = "http://localhost:8082/api/viajes/" + kcontext.getVariable("codigoViaje");
try {
  java.net.HttpURLConnection con = (java.net.HttpURLConnection) new java.net.URL(url).openConnection();
  con.setRequestMethod("GET");
''' + HTTP_HELPER + r'''  System.out.println("[MaritimaSOA] GET " + url + " -> " + code);
  if (code == 200) {
''' + "    " + campo_json("mT", "tipoRuta") + "    " + campo_json("mP", "codigoPuerto") + "    " + campo_json("mF", "fechaZarpe") + "    " + campo_json("mD", "paisDestino") + "    " + campo_json("mC", "cuposDisponibles", True) + r'''    if (mT.find()) kcontext.setVariable("tipoRuta", mT.group(1));
    if (mP.find()) kcontext.setVariable("codigoPuerto", mP.group(1));
    if (mF.find()) kcontext.setVariable("fechaZarpe", mF.group(1));
    if (mD.find()) kcontext.setVariable("paisDestino", mD.group(1));
    Integer cupos = mC.find() ? Integer.valueOf(mC.group(1)) : Integer.valueOf(0);
    kcontext.setVariable("cuposDisponibles", cupos);
    Integer pedidos = (Integer) kcontext.getVariable("cantidadAsientos");
    if (pedidos == null || cupos.intValue() < pedidos.intValue()) {
      kcontext.setVariable("motivoRechazo", "SIN_CUPOS: el viaje tiene " + cupos + " cupos");
    }
  } else {
    kcontext.setVariable("cuposDisponibles", Integer.valueOf(0));
    kcontext.setVariable("motivoRechazo", "Viaje no disponible: " + body);
  }
} catch (java.io.IOException e) {
  throw new RuntimeException("El servicio REST no responde (" + url + ")", e);
}
'''

SCRIPTS["T3"] = '// Consulta el estado del puerto en AutoridadPortuariaService (SOAP :8083)\n' + post_soap(
    '"<aut:consultarEstadoPuertoRequest><aut:codigoPuerto>" + kcontext.getVariable("codigoPuerto") + "</aut:codigoPuerto><aut:fechaZarpe>" + kcontext.getVariable("fechaZarpe") + "</aut:fechaZarpe></aut:consultarEstadoPuertoRequest>"'
) + r'''  System.out.println("[MaritimaSOA] SOAP consultarEstadoPuerto -> " + code);
  ''' + campo_xml("mA", "puertoAbierto") + "  " + campo_xml("mC", "condicionMaritima") + "  " + campo_xml("mZ", "codigoAutorizacionZarpe") + r'''  boolean abierto = mA.find() && "true".equals(mA.group(1).trim());
  kcontext.setVariable("puertoAbierto", Boolean.valueOf(abierto));
  if (mZ.find()) kcontext.setVariable("codigoAutorizacionZarpe", mZ.group(1));
  if (!abierto) {
    kcontext.setVariable("motivoRechazo", "PUERTO_CERRADO: " + (mC.find() ? mC.group(1) : "sin respuesta"));
  }
} catch (java.io.IOException e) {
  throw new RuntimeException("El servicio SOAP no responde (" + url + ")", e);
}
'''

SCRIPTS["T4"] = '// Valida el pasaporte en Migraciones (SOAP :8083), solo rutas internacionales\n' + post_soap(
    '"<aut:validarMigracionPasajeroRequest><aut:numeroPasaporte>" + kcontext.getVariable("numeroPasaporte") + "</aut:numeroPasaporte><aut:documentoIdentidad>" + kcontext.getVariable("documentoPasajero") + "</aut:documentoIdentidad><aut:paisDestino>" + kcontext.getVariable("paisDestino") + "</aut:paisDestino></aut:validarMigracionPasajeroRequest>"'
) + r'''  System.out.println("[MaritimaSOA] SOAP validarMigracionPasajero -> " + code);
  ''' + campo_xml("mH", "habilitadoViaje") + "  " + campo_xml("mM", "mensajeControl") + r'''  boolean habilitado = mH.find() && "true".equals(mH.group(1).trim());
  kcontext.setVariable("habilitadoViaje", Boolean.valueOf(habilitado));
  if (!habilitado) {
    kcontext.setVariable("motivoRechazo", "MIGRACION_RECHAZADA: " + (mM.find() ? mM.group(1) : "sin respuesta"));
  }
} catch (java.io.IOException e) {
  throw new RuntimeException("El servicio SOAP no responde (" + url + ")", e);
}
'''

SCRIPTS["T5"] = r'''// Emite el boleto en NavieraReservasAPI (REST :8082) y descuenta los cupos
String url = "http://localhost:8082/api/boletos";
try {
  String nombre = String.valueOf(kcontext.getVariable("nombrePasajero")).replace("\"", "'");
  String json = "{\"codigoViaje\":\"" + kcontext.getVariable("codigoViaje") + "\","
      + "\"documentoPasajero\":\"" + kcontext.getVariable("documentoPasajero") + "\","
      + "\"nombrePasajero\":\"" + nombre + "\","
      + "\"tipoRuta\":\"" + kcontext.getVariable("tipoRuta") + "\","
      + "\"cantidadAsientos\":" + kcontext.getVariable("cantidadAsientos") + ","
      + "\"codigoAutorizacionZarpe\":\"" + kcontext.getVariable("codigoAutorizacionZarpe") + "\"}";
  java.net.HttpURLConnection con = (java.net.HttpURLConnection) new java.net.URL(url).openConnection();
  con.setRequestMethod("POST");
  con.setDoOutput(true);
  con.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
  java.io.OutputStream out = con.getOutputStream();
  out.write(json.getBytes("UTF-8"));
  out.close();
''' + HTTP_HELPER + r'''  System.out.println("[MaritimaSOA] POST " + url + " -> " + code + " " + body);
  if (code != 201) {
    throw new RuntimeException("No se pudo emitir el boleto: " + body);
  }
''' + "  " + campo_json("mI", "idBoleto") + "  " + campo_json("mT", "montoTotal", True) + "  " + campo_json("mU", "muelleEmbarque") + r'''  if (mI.find()) kcontext.setVariable("idBoleto", mI.group(1));
  if (mT.find()) kcontext.setVariable("montoTotal", mT.group(1));
  if (mU.find()) kcontext.setVariable("muelleEmbarque", mU.group(1));
  kcontext.setVariable("estado", "EMITIDO");
} catch (java.io.IOException e) {
  throw new RuntimeException("El servicio REST no responde (" + url + ")", e);
}
'''

SCRIPTS["T6"] = r"""// Publica el aviso de embarque en ActiveMQ (cola.embarque.boletos) por STOMP, puerto 61613
String mensaje = "{\"idBoleto\":\"" + kcontext.getVariable("idBoleto") + "\",\"codigoViaje\":\""
    + kcontext.getVariable("codigoViaje") + "\",\"muelleEmbarque\":\"" + kcontext.getVariable("muelleEmbarque") + "\"}";
java.net.Socket socket = new java.net.Socket();
try {
  socket.connect(new java.net.InetSocketAddress("localhost", 61613), 3000);
  socket.setSoTimeout(5000);
  java.io.OutputStream out = socket.getOutputStream();
  java.io.InputStream in = socket.getInputStream();
  String[] tramas = {
    "CONNECT\naccept-version:1.2\nhost:localhost\nlogin:admin\npasscode:admin\n\n",
    "SEND\ndestination:/queue/cola.embarque.boletos\ncontent-type:application/json\nreceipt:aviso\n\n" + mensaje
  };
  String[] esperado = { "CONNECTED", "RECEIPT" };
  for (int i = 0; i < tramas.length; i++) {
    out.write(tramas[i].getBytes("UTF-8"));
    out.write(0);
    out.flush();
    StringBuilder resp = new StringBuilder();
    int b;
    while ((b = in.read()) > 0) resp.append((char) b);
    String r = resp.toString().trim();
    if (!r.startsWith(esperado[i])) throw new java.io.IOException("ActiveMQ respondió: " + r);
  }
  out.write("DISCONNECT\n\n".getBytes("UTF-8"));
  out.write(0);
  out.flush();
  System.out.println("[MaritimaSOA] ActiveMQ cola.embarque.boletos <- " + mensaje);
  kcontext.setVariable("avisoEmbarque", "PUBLICADO");
} catch (java.io.IOException e) {
  System.out.println("[MaritimaSOA] ActiveMQ no disponible: " + e.getMessage());
  kcontext.setVariable("avisoEmbarque", "NO_PUBLICADO (" + e.getMessage() + ")");
} finally {
  try { socket.close(); } catch (java.io.IOException ignorada) { }
}
"""

SCRIPTS["T7"] = r'''// Despacho genera el pase de embarque a partir del boleto
kcontext.setVariable("paseEmbarque", "PASE-" + kcontext.getVariable("idBoleto"));
System.out.println("[MaritimaSOA] Pase de embarque " + kcontext.getVariable("paseEmbarque"));
'''

SCRIPTS["T9"] = r'''// Rechazo por falta de cupos o puerto cerrado
kcontext.setVariable("estado", "RECHAZADA");
System.out.println("[MaritimaSOA] Venta RECHAZADA: " + kcontext.getVariable("motivoRechazo"));
'''

SCRIPTS["T10"] = r'''// Rechazo por control migratorio
kcontext.setVariable("estado", "RECHAZADA");
System.out.println("[MaritimaSOA] Venta RECHAZADA: " + kcontext.getVariable("motivoRechazo"));
'''

COND = {
    "f4": 'Integer c = (Integer) kcontext.getVariable("cuposDisponibles");\nInteger p = (Integer) kcontext.getVariable("cantidadAsientos");\nreturn c != null && p != null && c.intValue() >= p.intValue();',
    "f6": 'Integer c = (Integer) kcontext.getVariable("cuposDisponibles");\nInteger p = (Integer) kcontext.getVariable("cantidadAsientos");\nreturn !(c != null && p != null && c.intValue() >= p.intValue());',
    "f10": 'return Boolean.TRUE.equals(kcontext.getVariable("puertoAbierto"));',
    "f7": 'return !Boolean.TRUE.equals(kcontext.getVariable("puertoAbierto"));',
    "f12": 'return "INTERNACIONAL".equals(kcontext.getVariable("tipoRuta"));',
    "f11": 'return !"INTERNACIONAL".equals(kcontext.getVariable("tipoRuta"));',
    "f14": 'return Boolean.TRUE.equals(kcontext.getVariable("habilitadoViaje"));',
    "f15": 'return !Boolean.TRUE.equals(kcontext.getVariable("habilitadoViaje"));',
}

# ---------- estructura ----------
LANES = [
    ("Lane_Pasajero", "Pasajero", (50, 64, 1370, 130), ["Start", "T1", "T8", "End1"]),
    ("Lane_Naviera", "Naviera: plataforma de venta (REST)", (50, 194, 1370, 240),
     ["T2", "G1", "G2", "Gr", "T9", "End2", "G3", "Gm", "T5", "T6"]),
    ("Lane_Autoridad", "Autoridad Portuaria y Migraciones (SOAP)", (50, 434, 1370, 140), ["T3", "T4", "G4", "T10", "End3"]),
    ("Lane_Despacho", "Despacho de embarque (ActiveMQ)", (50, 574, 1370, 140), ["T7"]),
]
NODES = {  # id: (tipo, nombre, x, y, w, h)
    "Start": ("start", "Solicitud de pasaje", 112, 111, 36, 36),
    "T1": ("user", "Solicitar reserva de pasaje", 185, 95, 120, 68),
    "T2": ("script", "Consultar viaje y cupos [REST]", 185, 330, 120, 68),
    "G1": ("xor-div", "¿Hay cupos?", 340, 339, 50, 50),
    "T3": ("script", "Consultar estado del puerto [SOAP]", 305, 470, 120, 68),
    "G2": ("xor-div", "¿Puerto abierto?", 480, 339, 50, 50),
    "Gr": ("xor-conv", "", 480, 214, 50, 50),
    "T9": ("script", "Notificar rechazo al pasajero", 585, 205, 120, 68),
    "End2": ("end", "Venta rechazada (sin cupos o puerto cerrado)", 767, 221, 36, 36),
    "G3": ("xor-div", "¿Tipo de ruta?", 620, 339, 50, 50),
    "T4": ("script", "Validar migración del pasajero [SOAP]", 585, 470, 120, 68),
    "G4": ("xor-div", "¿Habilitado para viajar?", 760, 479, 50, 50),
    "Gm": ("xor-conv", "", 760, 339, 50, 50),
    "T10": ("script", "Notificar rechazo migratorio", 855, 470, 120, 68),
    "End3": ("end", "Venta rechazada (control migratorio)", 1002, 486, 36, 36),
    "T5": ("script", "Emitir boleto y descontar cupos [REST]", 855, 330, 120, 68),
    "T6": ("script", "Publicar aviso de embarque [ActiveMQ]", 1050, 330, 120, 68),
    "T7": ("script", "Generar pase de embarque", 1050, 610, 120, 68),
    "T8": ("user", "Recibir boleto y pase de embarque", 1200, 95, 120, 68),
    "End1": ("end", "Venta exitosa", 1347, 111, 36, 36),
}
FLOWS = [  # id, nombre, origen, destino, waypoints
    ("f1", "", "Start", "T1", [(148, 129), (185, 129)]),
    ("f2", "", "T1", "T2", [(245, 163), (245, 330)]),
    ("f3", "", "T2", "G1", [(305, 364), (340, 364)]),
    ("f4", "Sí", "G1", "T3", [(365, 389), (365, 470)]),
    ("f5", "", "T3", "G2", [(425, 504), (505, 504), (505, 389)]),
    ("f6", "No", "G1", "Gr", [(365, 339), (365, 239), (480, 239)]),
    ("f7", "No", "G2", "Gr", [(505, 339), (505, 264)]),
    ("f8", "", "Gr", "T9", [(530, 239), (585, 239)]),
    ("f9", "", "T9", "End2", [(705, 239), (767, 239)]),
    ("f10", "Sí", "G2", "G3", [(530, 364), (620, 364)]),
    ("f11", "Nacional", "G3", "Gm", [(670, 364), (760, 364)]),
    ("f12", "Internacional", "G3", "T4", [(645, 389), (645, 470)]),
    ("f13", "", "T4", "G4", [(705, 504), (760, 504)]),
    ("f14", "Sí", "G4", "Gm", [(785, 479), (785, 389)]),
    ("f15", "No", "G4", "T10", [(810, 504), (855, 504)]),
    ("f16", "", "T10", "End3", [(975, 504), (1002, 504)]),
    ("f17", "", "Gm", "T5", [(810, 364), (855, 364)]),
    ("f18", "", "T5", "T6", [(975, 364), (1050, 364)]),
    ("f19", "", "T6", "T7", [(1110, 398), (1110, 610)]),
    ("f20", "", "T7", "T8", [(1170, 644), (1260, 644), (1260, 163)]),
    ("f21", "", "T8", "End1", [(1320, 129), (1347, 129)]),
]

USER_TASKS = {
    "T1": {"task": "SolicitarReserva", "in": [],
           "out": ["codigoViaje", "cantidadAsientos", "documentoPasajero", "nombrePasajero", "numeroPasaporte"]},
    "T8": {"task": "RecibirBoleto",
           "in": ["estado", "idBoleto", "montoTotal", "muelleEmbarque", "paseEmbarque", "avisoEmbarque"], "out": []},
}


def meta(nombre):
    return (f'<bpmn2:extensionElements><drools:metaData name="elementname"><drools:metaValue>'
            f'<![CDATA[{nombre}]]></drools:metaValue></drools:metaData></bpmn2:extensionElements>')


def build():
    inc = {n: [] for n in NODES}
    out = {n: [] for n in NODES}
    for fid, _, s, t, _ in FLOWS:
        out[s].append(fid)
        inc[t].append(fid)
    L = []
    a = L.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a('<bpmn2:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
      'xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" '
      'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
      'xmlns:bpsim="http://www.bpsim.org/schemas/1.0" '
      'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
      'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
      'xmlns:drools="http://www.jboss.org/drools" '
      'id="_MaritimaSOA" exporter="jBPM Process Modeler" exporterVersion="2.0" '
      'targetNamespace="http://www.omg.org/bpmn20">')
    for v, t in VARS:
        a(f'  <bpmn2:itemDefinition id="_{v}Item" structureRef="{t}"/>')
    for tid, ut in USER_TASKS.items():
        a(f'  <bpmn2:itemDefinition id="__{tid}_TaskNameInputXItem" structureRef="Object"/>')
        a(f'  <bpmn2:itemDefinition id="__{tid}_SkippableInputXItem" structureRef="Object"/>')
        for v in ut["in"]:
            a(f'  <bpmn2:itemDefinition id="__{tid}_{v}InputXItem" structureRef="{VTYPE[v]}"/>')
        for v in ut["out"]:
            a(f'  <bpmn2:itemDefinition id="__{tid}_{v}OutputXItem" structureRef="{VTYPE[v]}"/>')
    a(f'  <bpmn2:process id="{PROC_ID}" drools:packageName="{PKG}" drools:version="1.0" drools:adHoc="false" '
      f'name="venta-pasajes-maritimos" isExecutable="true" processType="Public">')
    for v, _ in VARS:
        a(f'    <bpmn2:property id="{v}" itemSubjectRef="_{v}Item" name="{v}"/>')
    a('    <bpmn2:laneSet>')
    for lid, lname, _, refs in LANES:
        a(f'      <bpmn2:lane id="{lid}" name="{escape(lname)}">{meta(lname)}')
        for r in refs:
            a(f'        <bpmn2:flowNodeRef>{r}</bpmn2:flowNodeRef>')
        a('      </bpmn2:lane>')
    a('    </bpmn2:laneSet>')
    for fid, nom, s, t, _ in FLOWS:
        attrs = f'id="{fid}" sourceRef="{s}" targetRef="{t}"'
        if nom:
            attrs += f' name="{escape(nom)}"'
        if fid in COND:
            a(f'    <bpmn2:sequenceFlow {attrs}>{meta(nom)}'
              f'<bpmn2:conditionExpression xsi:type="bpmn2:tFormalExpression" language="http://www.java.com/java">'
              f'<![CDATA[{COND[fid]}]]></bpmn2:conditionExpression></bpmn2:sequenceFlow>')
        else:
            a(f'    <bpmn2:sequenceFlow {attrs}/>')
    for nid, (tipo, nom, *_r) in NODES.items():
        io = "".join(f'<bpmn2:incoming>{f}</bpmn2:incoming>' for f in inc[nid]) + \
             "".join(f'<bpmn2:outgoing>{f}</bpmn2:outgoing>' for f in out[nid])
        n = escape(nom)
        if tipo == "start":
            a(f'    <bpmn2:startEvent id="{nid}" name="{n}">{meta(nom)}{io}</bpmn2:startEvent>')
        elif tipo == "end":
            a(f'    <bpmn2:endEvent id="{nid}" name="{n}">{meta(nom)}{io}</bpmn2:endEvent>')
        elif tipo.startswith("xor"):
            d = "Diverging" if tipo == "xor-div" else "Converging"
            a(f'    <bpmn2:exclusiveGateway id="{nid}" name="{n}" gatewayDirection="{d}">{meta(nom)}{io}</bpmn2:exclusiveGateway>')
        elif tipo == "script":
            a(f'    <bpmn2:scriptTask id="{nid}" name="{n}" scriptFormat="http://www.java.com/java">{meta(nom)}{io}'
              f'<bpmn2:script><![CDATA[{SCRIPTS[nid]}]]></bpmn2:script></bpmn2:scriptTask>')
        elif tipo == "user":
            ut = USER_TASKS[nid]
            x = [f'    <bpmn2:userTask id="{nid}" name="{n}">{meta(nom)}{io}', '      <bpmn2:ioSpecification>']
            x.append(f'        <bpmn2:dataInput id="{nid}_TaskNameInputX" drools:dtype="Object" itemSubjectRef="__{nid}_TaskNameInputXItem" name="TaskName"/>')
            x.append(f'        <bpmn2:dataInput id="{nid}_SkippableInputX" drools:dtype="Object" itemSubjectRef="__{nid}_SkippableInputXItem" name="Skippable"/>')
            for v in ut["in"]:
                x.append(f'        <bpmn2:dataInput id="{nid}_{v}InputX" drools:dtype="{VTYPE[v]}" itemSubjectRef="__{nid}_{v}InputXItem" name="{v}"/>')
            for v in ut["out"]:
                x.append(f'        <bpmn2:dataOutput id="{nid}_{v}OutputX" drools:dtype="{VTYPE[v]}" itemSubjectRef="__{nid}_{v}OutputXItem" name="{v}"/>')
            x.append('        <bpmn2:inputSet>')
            for v in ["TaskName", "Skippable"] + ut["in"]:
                x.append(f'          <bpmn2:dataInputRefs>{nid}_{v}InputX</bpmn2:dataInputRefs>')
            x.append('        </bpmn2:inputSet>')
            x.append('        <bpmn2:outputSet>')
            for v in ut["out"]:
                x.append(f'          <bpmn2:dataOutputRefs>{nid}_{v}OutputX</bpmn2:dataOutputRefs>')
            x.append('        </bpmn2:outputSet>')
            x.append('      </bpmn2:ioSpecification>')
            for v in ut["in"]:
                x.append(f'      <bpmn2:dataInputAssociation><bpmn2:sourceRef>{v}</bpmn2:sourceRef><bpmn2:targetRef>{nid}_{v}InputX</bpmn2:targetRef></bpmn2:dataInputAssociation>')
            for nombre_in, valor in (("TaskName", ut["task"]), ("Skippable", "false")):
                x.append(f'      <bpmn2:dataInputAssociation><bpmn2:targetRef>{nid}_{nombre_in}InputX</bpmn2:targetRef>'
                         f'<bpmn2:assignment><bpmn2:from xsi:type="bpmn2:tFormalExpression"><![CDATA[{valor}]]></bpmn2:from>'
                         f'<bpmn2:to xsi:type="bpmn2:tFormalExpression"><![CDATA[{nid}_{nombre_in}InputX]]></bpmn2:to></bpmn2:assignment></bpmn2:dataInputAssociation>')
            for v in ut["out"]:
                x.append(f'      <bpmn2:dataOutputAssociation><bpmn2:sourceRef>{nid}_{v}OutputX</bpmn2:sourceRef><bpmn2:targetRef>{v}</bpmn2:targetRef></bpmn2:dataOutputAssociation>')
            x.append(f'      <bpmn2:potentialOwner id="_{nid}_owner"><bpmn2:resourceAssignmentExpression>'
                     f'<bpmn2:formalExpression>wbadmin</bpmn2:formalExpression></bpmn2:resourceAssignmentExpression></bpmn2:potentialOwner>')
            x.append('    </bpmn2:userTask>')
            L.extend(x)
    a('  </bpmn2:process>')
    a('  <bpmndi:BPMNDiagram><bpmndi:BPMNPlane bpmnElement="%s">' % PROC_ID)
    for lid, _, (x, y, w, h), _ in LANES:
        a(f'    <bpmndi:BPMNShape id="shape_{lid}" bpmnElement="{lid}" isHorizontal="true"><dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}"/></bpmndi:BPMNShape>')
    for nid, (_, _, x, y, w, h) in NODES.items():
        a(f'    <bpmndi:BPMNShape id="shape_{nid}" bpmnElement="{nid}"><dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}"/></bpmndi:BPMNShape>')
    for fid, _, _, _, wps in FLOWS:
        pts = "".join(f'<di:waypoint x="{px}" y="{py}"/>' for px, py in wps)
        a(f'    <bpmndi:BPMNEdge id="edge_{fid}" bpmnElement="{fid}">{pts}</bpmndi:BPMNEdge>')
    a('  </bpmndi:BPMNPlane></bpmndi:BPMNDiagram>')
    a('</bpmn2:definitions>')
    return "\n".join(L) + "\n"


def java_check(carpeta):
    """Escribe una clase con cada script y condición para compilarla con javac --release 8."""
    os.makedirs(carpeta, exist_ok=True)
    c = ['public class ChequeoScripts {',
         '  interface Ctx { Object getVariable(String n); void setVariable(String n, Object v); }']
    for k, s in SCRIPTS.items():
        c.append(f'  static void s_{k}(Ctx kcontext) {{\n{s}\n  }}')
    for k, s in COND.items():
        c.append(f'  static boolean c_{k}(Ctx kcontext) {{\n{s}\n  }}')
    c.append('}')
    open(os.path.join(carpeta, "ChequeoScripts.java"), "w", encoding="utf-8").write("\n".join(c))


if __name__ == "__main__":
    open(sys.argv[1], "w", encoding="utf-8").write(build())
    if len(sys.argv) > 2:
        java_check(sys.argv[2])
