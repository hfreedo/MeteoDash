"""
MeteoDash Launcher - Menu interactivo de despliegue
"""
import subprocess
import sys
import os
import time
import webbrowser
import socket
import shutil

BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def tool_installed(name):
    return shutil.which(name) is not None

def get_base_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        # Buscar backend: mismo dir que el exe, o un nivel arriba (dist/)
        for base in [exe_dir, os.path.dirname(exe_dir)]:
            if os.path.isdir(os.path.join(base, "backend")):
                return base
        return exe_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))

def start_server():
    base = get_base_dir()
    backend = os.path.join(base, "backend")
    if not os.path.isdir(backend):
        print(f"\n  {RED}ERROR: No se encontro la carpeta 'backend'{RESET}")
        print(f"  Buscada en: {backend}")
        print(f"  El .exe debe estar junto a la carpeta 'backend'")
        print(f"  {YELLOW}Presiona Enter...{RESET}")
        input()
        return None
    print(f"  Backend encontrado en: {backend}")
    return subprocess.Popen(
        [sys.executable, "main.py"], cwd=backend,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{CYAN}")
    print("  +============================================+")
    print("  |       SISTEMA METEOROLOGICO                |")
    print("  |       Panel de Despliegue                  |")
    print("  +============================================+")
    print(f"{RESET}")

def menu():
    print_banner()
    print(f"  {BOLD}Elige modo de despliegue:{RESET}\n")

    has_cloudflared = tool_installed("cloudflared")
    has_ngrok = tool_installed("ngrok")

    print(f"  {GREEN}[1]{RESET}  Exposicion Local (WiFi Hotspot)")
    print(f"       Sin internet. Activa Zona movil en Windows.")
    print(f"       Visitantes se conectan al WiFi de la PC.\n")

    c_status = f"{GREEN}DISPONIBLE{RESET}" if has_cloudflared else f"{RED}NO INSTALADO{RESET}"
    print(f"  {CYAN}[2]{RESET}  Cloudflare Tunnel ({c_status})")
    print(f"       URL publica HTTPS desde cualquier parte.")
    if not has_cloudflared:
        print(f"       {YELLOW}Para instalar: winget install cloudflared{RESET}")
    print()

    print(f"  {YELLOW}[3]{RESET}  Serveo (SSH, sin instalar nada)")
    print(f"       URL publica via SSH. Ya incluido en Windows.\n")

    n_status = f"{GREEN}DISPONIBLE{RESET}" if has_ngrok else f"{RED}NO INSTALADO{RESET}"
    print(f"  [4]  Ngrok ({n_status})")
    if not has_ngrok:
        print(f"       {YELLOW}Descarga: https://ngrok.com/download{RESET}")
    print()

    print(f"  [5]  Solo desarrollo (localhost)\n")
    print(f"  {RED}[0]{RESET}  Salir\n")

def run_local(ip):
    print(f"\n  {GREEN}Servidor iniciado en:{RESET}")
    print(f"  Local:   {BOLD}http://localhost:8000{RESET}")
    print(f"  Red:     {BOLD}http://{ip}:8000{RESET}")
    print(f"\n  {YELLOW}Para exposicion:{RESET}")
    print(f"  1. Ve a Configuracion > Red > Zona movil")
    print(f"  2. Activa el hotspot")
    print(f"  3. Visitantes se conectan a esa WiFi")
    print(f"  4. Abren {BOLD}http://{ip}:8000{RESET}")
    print(f"\n  {RED}Ctrl+C para detener{RESET}\n")

def install_tool(name, install_cmd, exe_name):
    print(f"\n  {RED}{name} no esta instalado.{RESET}")
    ans = input(f"  Quieres instalarlo ahora? (s/n): ").strip().lower()
    if ans == "s":
        # Escribir un .bat temporal y ejecutarlo en ventana aparte
        bat_path = os.path.join(os.environ.get("TEMP", "."), f"install_{exe_name}.bat")
        with open(bat_path, "w") as f:
            f.write(f"@echo off\n")
            f.write(f"echo Instalando {name}...\n")
            f.write(f"{install_cmd}\n")
            f.write(f"echo.\n")
            f.write(f"echo Instalacion completada. Cierra esta ventana y reabre MeteoDash.\n")
            f.write(f"pause\n")
        os.startfile(bat_path)
        print(f"  {GREEN}Ventana de instalacion abierta.{RESET}")
        print(f"  {YELLOW}Al terminar, CIERRA y REABRE MeteoDash.{RESET}")
    print(f"  {YELLOW}Presiona Enter para volver al menu...{RESET}")
    input()
    return False

def run_tunnel(cmd, name, install_cmd=None, exe_name=None):
    print(f"\n  {CYAN}Iniciando {name}...{RESET}")
    print(f"\n  {MAGENTA}{'='*55}{RESET}")
    print(f"  {BOLD}EL TUNEL ESTA ARRANCANDO.{RESET}")
    print(f"  Busca una linea como esta en la salida:")
    print(f"  {GREEN}https://xxxxx.trycloudflare.com{RESET}")
    print(f"  {YELLOW}Esa URL se la das a los visitantes.{RESET}")
    print(f"  {RED}Ctrl+C para detener todo.{RESET}")
    print(f"  {MAGENTA}{'='*55}{RESET}\n")
    webbrowser.open("http://localhost:8000")
    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        if install_cmd:
            install_tool(name, install_cmd, exe_name)
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Tunel detenido.{RESET}")
    except Exception as e:
        print(f"\n  {RED}Error: {e}{RESET}")
        input()

def main():
    while True:
        menu()
        try:
            opt = input("  Opcion > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {RED}Adios!{RESET}")
            break

        if opt == "0":
            print(f"\n  {RED}Adios!{RESET}")
            break

        if opt not in ("1","2","3","4","5"):
            print(f"\n  {RED}Opcion no valida{RESET}")
            time.sleep(1)
            continue

        print(f"\n  {CYAN}Iniciando servidor...{RESET}")
        server = start_server()
        time.sleep(3)
        ip = get_ip()

        if opt == "1":
            run_local(ip)
            webbrowser.open("http://localhost:8000")
            try:
                server.wait()
            except KeyboardInterrupt:
                pass
            finally:
                server.terminate()
                server.wait()

        elif opt == "2":
            run_tunnel(
                ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
                "Cloudflare Tunnel",
                "winget install --accept-source-agreements --accept-package-agreements Cloudflare.cloudflared",
                "cloudflared"
            )
            server.terminate()
            server.wait()

        elif opt == "3":
            run_tunnel(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8000", "serveo.net"],
                "Serveo"
            )
            server.terminate()
            server.wait()

        elif opt == "4":
            run_tunnel(
                ["ngrok", "http", "8000"],
                "Ngrok",
                "winget install --accept-source-agreements --accept-package-agreements ngrok.ngrok",
                "ngrok"
            )
            server.terminate()
            server.wait()

        elif opt == "5":
            print(f"\n  {GREEN}Servidor en http://localhost:8000{RESET}")
            print(f"  {RED}Ctrl+C para detener{RESET}\n")
            webbrowser.open("http://localhost:8000")
            try:
                server.wait()
            except KeyboardInterrupt:
                pass
            finally:
                server.terminate()
                server.wait()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {RED}Adios!{RESET}")
    except Exception as e:
        print(f"\n  {RED}{'='*50}{RESET}")
        print(f"  {RED}ERROR INESPERADO:{RESET}")
        print(f"  {RED}{e}{RESET}")
        import traceback
        traceback.print_exc()
        print(f"  {RED}{'='*50}{RESET}")
        print(f"\n  {YELLOW}Presiona Enter para salir...{RESET}")
        input()
