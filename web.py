import schedule
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket

# Configurar Selenium
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Ejecutar sin abrir el navegador
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Verificar el estado de las URLs
def check_urls(urls_with_names):
    driver = setup_driver()
    results = []
    for name, url in urls_with_names:
        try:
            driver.get(url)
            results.append((name, url, "Funciona", driver.title))
        except WebDriverException as e:
            results.append((name, url, "Error", str(e)))
    driver.quit()
    return results

# Verificar conexión al servidor SMTP
def verify_smtp_connection(smtp_server, smtp_port, timeout=10):
    try:
        with socket.create_connection((smtp_server, smtp_port), timeout=timeout):
            print(f"✅ Conexión establecida con el servidor SMTP {smtp_server}:{smtp_port}")
            return True
    except socket.error as e:
        print(f"❌ Error al conectar con el servidor SMTP: {e}")
        return False

# Enviar correo de notificación
def send_email(subject, body, to_emails, from_email, from_password, smtp_server, smtp_port):
    if not verify_smtp_connection(smtp_server, smtp_port):
        print("❌ No se pudo conectar al servidor SMTP.")
        return

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(from_email, from_password)
            server.sendmail(from_email, to_emails, msg.as_string())
        print("✅ Correo enviado con éxito.")
    except smtplib.SMTPException as e:
        print(f"❌ Error al enviar el correo: {e}")

# Función principal para ejecutar cada minuto
def job():
    print("🔄 Ejecutando la verificación...")
    urls_with_names = [
        ("Portar E2E", "http://10.202.50.82:443"),
        ("META", "http://10.202.50.82:8501"),
        ("VOLTE", "http://10.202.50.82:8503"),
        ("GPON", "http://10.202.50.82:8505"),
        ("Pre Origin", "http://10.202.50.82:8080"),
        ("Trafico", "http://10.202.50.82:8513")
        
    ]
    results = check_urls(urls_with_names)

    # Convertir resultados a DataFrame
    df = pd.DataFrame(results, columns=["Nombre", "URL", "Estado", "Título"])
    print(df)

    # Enviar correo si hay errores
    errores = df[df["Estado"] == "Error"]
    if not errores.empty:
        error_details = "\n".join(
            f"{row['Nombre']} ({row['URL']})" for _, row in errores.iterrows()
        )
        email_subject = "⚠️ Alerta: Páginas Caídas Detectadas"
        email_body = f"Las siguientes páginas están caídas:\n\n{error_details}"
        team_emails = ["calidaddeservicio@claro.com.ar"]
        from_email = "claro.calidaddeservicios@gmail.com"
        from_password = "kjvljjcvfesujoaa"
        smtp_server = "smtp.gmail.com"
        smtp_port = 465

        send_email(email_subject, email_body, team_emails, from_email, from_password, smtp_server, smtp_port)

# Programar la tarea para que se ejecute cada 10 minuto
schedule.every(10).minutes.do(job)

# Loop infinito para mantener el script ejecutándose
print("⏳ Iniciando el chequeo...")
while True:
    schedule.run_pending()
    time.sleep(1)
