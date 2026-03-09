"""
╔══════════════════════════════════════════════════════╗
║         ANTI-DISTRAÇÃO - Detector de Foco            ║
║         + Alertas em vídeo MP4                       ║
╚══════════════════════════════════════════════════════╝

DEPENDÊNCIAS:
    pip install opencv-python pygame numpy

COMO CONFIGURAR OS VÍDEOS:
    Coloque os arquivos MP4 na mesma pasta que este script.

ESTRUTURA DA PASTA:
    📁 Downloads/
       ├── anti_distracao.py
       ├── alerta_rosto.mp4
       ├── alerta_olhos.mp4
       └── alerta_sono.mp4
"""

import cv2
import numpy as np
import time
import sys
import os

try:
    import pygame
    pygame.mixer.init()
    TEM_PYGAME = True
except ImportError:
    TEM_PYGAME = False

# ─────────────────────────────────────────────────────────────
# PASTA DO SCRIPT — garante que os vídeos sejam encontrados
# independente de onde o terminal foi aberto
# ─────────────────────────────────────────────────────────────
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))

def caminho(nome_arquivo):
    """Retorna o caminho completo do arquivo na pasta do script."""
    return os.path.join(PASTA_SCRIPT, nome_arquivo)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES GERAIS
# ─────────────────────────────────────────────────────────────
TEMPO_GRACA           = 1.5
TEMPO_COOLDOWN        = 4.0
SENSIBILIDADE         = 0.30
TEMPO_OLHOS_FECHADOS  = 2.0
TEMPO_SONOLENCIA      = 2.5
LIMIAR_SONOLENCIA     = 0.60

COR_OK     = (0, 220, 100)
COR_ALERTA = (0, 60, 255)
COR_AVISO  = (0, 200, 255)
COR_SONO   = (0, 165, 255)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DE VÍDEO
# ─────────────────────────────────────────────────────────────
VIDEO_ROSTO = "alerta_rosto.mp4"
VIDEO_OLHOS = "alerta_olhos.mp4"
VIDEO_SONO  = "alerta_sono.mp4"

TAMANHO_VIDEO = (320, 240)
POSICAO_VIDEO = "centro"   # "centro", "topo-direita", "topo-esquerda"
LOOP_VIDEO    = True


# ─────────────────────────────────────────────────────────────
# DETECTORES DO OPENCV
# ─────────────────────────────────────────────────────────────
base              = cv2.data.haarcascades
detector_rosto    = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
detector_olho_esq = cv2.CascadeClassifier(base + "haarcascade_lefteye_2splits.xml")
detector_olho_dir = cv2.CascadeClassifier(base + "haarcascade_righteye_2splits.xml")

if detector_rosto.empty():
    print("Erro: OpenCV nao encontrado. Reinstale o opencv-python.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# PLAYER DE VÍDEO
# ─────────────────────────────────────────────────────────────
class PlayerVideo:
    def __init__(self):
        self.cap     = None
        self.arquivo = None

    def proximo_frame(self, nome_arquivo):
        caminho_completo = caminho(nome_arquivo)  # ← usa sempre a pasta do script

        if not os.path.exists(caminho_completo):
            return None

        # Abre o vídeo se ainda não está aberto ou se mudou
        if self.arquivo != caminho_completo:
            if self.cap:
                self.cap.release()
            self.cap     = cv2.VideoCapture(caminho_completo)
            self.arquivo = caminho_completo

        ret, frame = self.cap.read()

        if not ret:
            if LOOP_VIDEO:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return None
            else:
                return None

        return cv2.resize(frame, TAMANHO_VIDEO)

    def resetar(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.arquivo = None


player = PlayerVideo()


# ─────────────────────────────────────────────────────────────
# SOBREPOSIÇÃO DO VÍDEO
# ─────────────────────────────────────────────────────────────
def sobrepor_video(frame_webcam, nome_video):
    frame_video = player.proximo_frame(nome_video)

    if frame_video is None:
        desenhar_alerta_texto(frame_webcam, "! ATENCAO !", COR_ALERTA)
        return

    h_cam, w_cam = frame_webcam.shape[:2]
    vw, vh       = TAMANHO_VIDEO

    if POSICAO_VIDEO == "centro":
        px, py = (w_cam - vw) // 2, (h_cam - vh) // 2
    elif POSICAO_VIDEO == "topo-direita":
        px, py = w_cam - vw - 10, 10
    elif POSICAO_VIDEO == "topo-esquerda":
        px, py = 10, 10
    else:
        px, py = (w_cam - vw) // 2, (h_cam - vh) // 2

    cv2.rectangle(frame_webcam, (px-4, py-4), (px+vw+4, py+vh+4), COR_ALERTA, 3)
    frame_webcam[py:py+vh, px:px+vw] = frame_video


def desenhar_alerta_texto(frame, mensagem, cor):
    overlay = frame.copy()
    h, w    = frame.shape[:2]
    cv2.rectangle(overlay, (0, 0), (w, h), cor, -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
    cv2.rectangle(frame, (10, 10), (w-10, h-10), cor, 4)
    fonte     = cv2.FONT_HERSHEY_DUPLEX
    (tw, _), _ = cv2.getTextSize(mensagem, fonte, 1.3, 3)
    tx = (w - tw) // 2
    cv2.putText(frame, mensagem, (tx+3, h//2+3), fonte, 1.3, (0,0,0), 5)
    cv2.putText(frame, mensagem, (tx,   h//2),   fonte, 1.3, (255,255,255), 3)


# ─────────────────────────────────────────────────────────────
# HUD E BARRAS
# ─────────────────────────────────────────────────────────────
def desenhar_hud(frame, linhas):
    fonte = cv2.FONT_HERSHEY_SIMPLEX
    h, w  = frame.shape[:2]
    for texto, cor, py in linhas:
        cv2.putText(frame, texto, (20, py), fonte, 0.65, cor, 2)
    cv2.putText(frame, "Q = sair", (w - 110, 30), fonte, 0.55, (150,150,150), 1)


def desenhar_barra(frame, label, valor, maximo, cor, bx, by):
    bar_total = 180
    bar_fill  = int(bar_total * min(valor / maximo, 1.0))
    cv2.putText(frame, label, (bx, by-6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180,180,180), 1)
    cv2.rectangle(frame, (bx, by), (bx+bar_total, by+14), (50,50,50), -1)
    cv2.rectangle(frame, (bx, by), (bx+bar_fill,  by+14), cor, -1)


# ─────────────────────────────────────────────────────────────
# BEEP
# ─────────────────────────────────────────────────────────────
def tocar_alerta(frequencia=880):
    if TEM_PYGAME:
        sample_rate = 44100
        t      = np.linspace(0, 0.4, int(sample_rate * 0.4))
        onda   = (np.sin(2 * np.pi * frequencia * t) * 32767 * 0.8).astype(np.int16)
        stereo = np.column_stack([onda, onda])
        pygame.sndarray.make_sound(stereo).play()
    else:
        print("\a", end="", flush=True)


# ─────────────────────────────────────────────────────────────
# ANÁLISE DOS OLHOS
# ─────────────────────────────────────────────────────────────
def analisar_olhos(cinza, x, y, rw, rh):
    roi       = cinza[y:y+rh, x:x+rw]
    olhos_esq = detector_olho_esq.detectMultiScale(roi, 1.1, 3, minSize=(20, 10))
    olhos_dir = detector_olho_dir.detectMultiScale(roi, 1.1, 3, minSize=(20, 10))
    alt_esq   = olhos_esq[0][3] if len(olhos_esq) > 0 else None
    alt_dir   = olhos_dir[0][3] if len(olhos_dir) > 0 else None
    return alt_esq, alt_dir, (alt_esq is not None and alt_dir is not None)


# ─────────────────────────────────────────────────────────────
# CALIBRAÇÃO
# ─────────────────────────────────────────────────────────────
def calibrar(cap):
    print("\nCalibrando... Olhe para a camera com os olhos bem abertos!")

    amostras_area  = []
    amostras_olhos = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame  = cv2.flip(frame, 1)
        h, w   = frame.shape[:2]
        cinza  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rostos = detector_rosto.detectMultiScale(cinza, 1.1, 5, minSize=(80, 80))

        cv2.putText(frame, "Abra bem os olhos e olhe para a camera!",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)

        if len(rostos) == 1:
            x, y, rw, rh                 = rostos[0]
            alt_esq, alt_dir, dois_olhos = analisar_olhos(cinza, x, y, rw, rh)

            if dois_olhos:
                amostras_area.append(rw * rh)
                amostras_olhos.append((alt_esq + alt_dir) / 2)

            progresso = min(len(amostras_area) / 25, 1.0)
            bar_w     = int((w - 40) * progresso)
            cv2.rectangle(frame, (20, h-50), (w-20, h-20), (50,50,50), -1)
            cv2.rectangle(frame, (20, h-50), (20+bar_w, h-20), COR_OK, -1)
            cv2.putText(frame, f"Calibrando: {int(progresso*100)}%",
                        (20, h-55), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200,200,200), 1)
            cv2.rectangle(frame, (x, y), (x+rw, y+rh), COR_OK, 2)

            if len(amostras_area) >= 25:
                break

        cv2.imshow("Anti-Distracao", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    print("Calibracao concluida!\n")
    return np.mean(amostras_area), np.mean(amostras_olhos)


# ─────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  ANTI-DISTRACAO COM VIDEO DE ALERTA")
    print(f"  Pasta dos arquivos: {PASTA_SCRIPT}")
    print("=" * 55)

    # Mostra quais vídeos foram encontrados
    for v in [VIDEO_ROSTO, VIDEO_OLHOS, VIDEO_SONO]:
        status = "[OK]" if os.path.exists(caminho(v)) else "[NAO ENCONTRADO]"
        print(f"  {status} {v}")
    print()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Nao foi possivel acessar a webcam!")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    area_base, altura_olho_base = calibrar(cap)
    limite_area       = area_base * (1.0 - SENSIBILIDADE)
    limite_sonolencia = altura_olho_base * LIMIAR_SONOLENCIA

    ultimo_alerta         = 0
    inicio_desviando      = None
    inicio_olhos_fechados = None
    inicio_sonolencia     = None
    sem_rosto_desde       = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        rostos = detector_rosto.detectMultiScale(
            cinza, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        agora       = time.time()
        em_alerta   = False
        video_atual = None
        linhas_hud  = []

        # ── Sem rosto ──────────────────────────────────────────
        if len(rostos) == 0:
            if sem_rosto_desde is None:
                sem_rosto_desde = agora
            tempo_sumido = agora - sem_rosto_desde

            if tempo_sumido >= TEMPO_GRACA:
                em_alerta   = True
                video_atual = VIDEO_ROSTO
                linhas_hud.append((f"Rosto sumido: {tempo_sumido:.1f}s", COR_ALERTA, h-20))
                if agora - ultimo_alerta > TEMPO_COOLDOWN:
                    tocar_alerta(880)
                    ultimo_alerta = agora
            else:
                linhas_hud.append(("Procurando rosto...", COR_AVISO, h-20))

            inicio_desviando      = None
            inicio_olhos_fechados = None
            inicio_sonolencia     = None

        # ── Rosto detectado ────────────────────────────────────
        else:
            sem_rosto_desde = None
            x, y, rw, rh    = max(rostos, key=lambda r: r[2]*r[3])
            area_atual       = rw * rh

            cv2.rectangle(frame, (x, y), (x+rw, y+rh), COR_OK, 2)

            alt_esq, alt_dir, dois_olhos = analisar_olhos(cinza, x, y, rw, rh)

            # 1. Rosto virado
            virou = area_atual < limite_area
            if virou:
                if inicio_desviando is None:
                    inicio_desviando = agora
                tempo_desviando = agora - inicio_desviando
                if tempo_desviando >= TEMPO_GRACA:
                    em_alerta   = True
                    video_atual = VIDEO_ROSTO
                    linhas_hud.append((f"Distraido: {tempo_desviando:.1f}s", COR_ALERTA, h-20))
                    if agora - ultimo_alerta > TEMPO_COOLDOWN:
                        tocar_alerta(880)
                        ultimo_alerta = agora
                else:
                    linhas_hud.append(("Atencao...", COR_AVISO, h-20))
            else:
                inicio_desviando = None

            # 2. Olhos fechados
            if not virou and not dois_olhos:
                if inicio_olhos_fechados is None:
                    inicio_olhos_fechados = agora
                tempo_fechados = agora - inicio_olhos_fechados
                if tempo_fechados >= TEMPO_OLHOS_FECHADOS:
                    em_alerta   = True
                    video_atual = VIDEO_OLHOS
                    linhas_hud.append((f"Olhos fechados: {tempo_fechados:.1f}s", COR_ALERTA, h-50))
                    if agora - ultimo_alerta > TEMPO_COOLDOWN:
                        tocar_alerta(660)
                        ultimo_alerta = agora
                else:
                    linhas_hud.append((f"Olhos fechando... {tempo_fechados:.1f}s", COR_AVISO, h-50))
            else:
                inicio_olhos_fechados = None

            # 3. Sonolência
            if not virou and dois_olhos:
                media_altura = (alt_esq + alt_dir) / 2
                desenhar_barra(frame, "Abertura dos olhos",
                               media_altura, altura_olho_base,
                               COR_OK if media_altura >= limite_sonolencia else COR_SONO,
                               20, h-100)

                if media_altura < limite_sonolencia:
                    if inicio_sonolencia is None:
                        inicio_sonolencia = agora
                    tempo_sono = agora - inicio_sonolencia
                    if tempo_sono >= TEMPO_SONOLENCIA:
                        em_alerta   = True
                        video_atual = VIDEO_SONO
                        linhas_hud.append((f"Sonolencia: {tempo_sono:.1f}s", COR_SONO, h-75))
                        if agora - ultimo_alerta > TEMPO_COOLDOWN:
                            tocar_alerta(550)
                            ultimo_alerta = agora
                    else:
                        linhas_hud.append(("Com sono...", COR_SONO, h-75))
                else:
                    inicio_sonolencia = None

            desenhar_barra(frame, "Angulo do rosto",
                           area_atual, area_base,
                           COR_OK if area_atual >= limite_area else COR_ALERTA,
                           20, h-135)

            if not em_alerta and not virou and dois_olhos:
                linhas_hud.append(("Focado  v", COR_OK, h-20))

        # ── Exibição final ─────────────────────────────────────
        if em_alerta and video_atual:
            sobrepor_video(frame, video_atual)
        elif not em_alerta:
            player.resetar()

        desenhar_hud(frame, linhas_hud)
        cv2.imshow("Anti-Distracao", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nEncerrado. Ate logo!")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
