import os
import sys
import time
import random
import math
import pygame as pg


WIDTH, HEIGHT = 1100, 650
DELTA = {
    pg.K_UP: (0, -5),
    pg.K_DOWN: (0, 5),
    pg.K_LEFT: (-5, 0),
    pg.K_RIGHT: (5, 0),
}
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    引数：こうかとんRectまたは爆弾Rect
    戻り値：タプル（横方向判定結果，縦方向判定結果）
    画面内ならTrue, 画面外ならFalse
    """
    yoko = True
    tate = True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def gameover(screen: pg.Surface) -> None:
    """ゲームオーバー画面を5秒間表示する。

    画面をブラックアウトし，泣いているこうかとん画像と
    「Game Over」の文字を重ねて表示する。

    Args:
        screen: 描画対象のメインSurface。
    """
    bb_surface = pg.Surface(screen.get_size())
    pg.draw.rect(bb_surface, (0, 0, 0), bb_surface.get_rect())
    bb_surface.set_alpha(200)

    font = pg.font.SysFont("notosanscjkjp", 80)
    txt_surface = font.render("Game Over", True, (255, 255, 255))
    txt_rect = txt_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    bb_surface.blit(txt_surface, txt_rect)

    sad_kk = pg.transform.rotozoom(pg.image.load("fig/8.png"), 0, 0.9)
    kk_rect = sad_kk.get_rect(center=(txt_rect.left - 60, screen.get_height() // 2))
    bb_surface.blit(sad_kk, kk_rect)
    kk_rect2 = sad_kk.get_rect(center=(txt_rect.right + 60, screen.get_height() // 2))
    bb_surface.blit(sad_kk, kk_rect2)

    screen.blit(bb_surface, (0, 0))
    pg.display.update()
    time.sleep(5)


def init_bb_imgs() -> tuple[list[pg.Surface], list[int]]:
    """10段階の爆弾Surfaceリストと加速度リストを初期化して返す。

    爆弾は時間経過とともに半径10〜100px, 加速度1〜10倍まで段階的に変化する。

    Returns:
        (bb_imgs, bb_accs): 爆弾Surfaceのリストと加速度のリストのタプル。
    """
    bb_imgs: list[pg.Surface] = []
    for r in range(1, 11):
        bb_img = pg.Surface((20 * r, 20 * r), pg.SRCALPHA)
        pg.draw.circle(bb_img, (255, 0, 0), (10 * r, 10 * r), 10 * r)
        bb_imgs.append(bb_img)

    bb_accs = [a for a in range(1, 11)]
    return bb_imgs, bb_accs


def get_kk_imgs() -> dict[tuple[int, int], pg.Surface]:
    """移動量タプルをキー, 対応する方向のこうかとんSurfaceを値とした辞書を返す。

    こうかとんは移動方向に合わせて9方向に回転した画像を持つ。

    Returns:
        移動量 (vx, vy) → 回転済みSurface の辞書。
    """
    kk_base = pg.image.load("fig/3.png")

    # (dx, dy) → 回転角度 (反時計回り，pygame座標系ではy軸が下向き)
    directions: dict[tuple[int, int], float] = {
        (0,   0):   0,
        (+5,  0):   0,
        (+5, -5):  45,
        (0,  -5):  90,
        (-5, -5): 135,
        (-5,  0): 180,
        (-5, +5): 225,
        (0,  +5): 270,
        (+5, +5): 315,
    }
    return {mv: pg.transform.rotozoom(kk_base, angle, 1.0) for mv, angle in directions.items()}


def calc_orientation(
    org: pg.Rect,
    dst: pg.Rect,
    current_xy: tuple[float, float],
) -> tuple[float, float]:
    """爆弾がこうかとんへ向かう正規化済み方向ベクトルを返す。

    距離が300未満のときは慣性（current_xy）をそのまま返し,
    急接近によるゲームオーバーを防ぐ。速度ベクトルのノルムは√50。

    Args:
        org: 爆弾のRect（移動元）。
        dst: こうかとんのRect（目標）。
        current_xy: 現在の移動方向ベクトル (vx, vy)。

    Returns:
        新しい方向ベクトル (vx, vy)。
    """
    dx = dst.centerx - org.centerx
    dy = dst.centery - org.centery
    dist = math.hypot(dx, dy)

    if dist < 300:
        return current_xy

    scale = math.sqrt(50) / dist
    return dx * scale, dy * scale


def main():
    pg.display.set_caption("逃げろ！こうかとん")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load("fig/pg_bg.jpg")    
    kk_imgs = get_kk_imgs()
    kk_img = kk_imgs[(0, 0)]
    kk_rct = kk_img.get_rect()
    kk_rct.center = 300, 200

    bb_img = pg.Surface((20, 20))
    pg.draw.circle(bb_img, (255, 0, 0), (10, 10), 10)
    bb_img.set_colorkey((0, 0, 0))
    bb_rct = bb_img.get_rect()
    bb_rct.centerx = random.randint(0, WIDTH)  # 爆弾の初期横座標を設定する
    bb_rct.centery = random.randint(0, HEIGHT)  # 爆弾の初期縦座標を設定する
    bb_vxy = (+5.0, +5.0)  # 爆弾の速度ベクトル
    bb_imgs, bb_accs = init_bb_imgs()

    clock = pg.time.Clock()
    tmr = 0
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT: 
                return
        screen.blit(bg_img, [0, 0]) 

        key_lst = pg.key.get_pressed()
        sum_mv = [0, 0]
        for key, mv in DELTA.items():
            if key_lst[key]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        kk_img = kk_imgs[tuple(sum_mv)]  # type: ignore[index]
        kk_rct.move_ip(sum_mv)
        if check_bound(kk_rct) != (True, True):  # 画面外だったら
            kk_rct.move_ip(-sum_mv[0], -sum_mv[1])
 
        screen.blit(kk_img, kk_rct)
        level = min(tmr // 500, 9)
        bb_img = bb_imgs[level]
        bb_rct.width = bb_img.get_rect().width
        bb_rct.height = bb_img.get_rect().height

        bb_vxy = calc_orientation(bb_rct, kk_rct, bb_vxy)
        vx, vy = bb_vxy
        avx = vx * bb_accs[level]
        avy = vy * bb_accs[level]
        bb_rct.move_ip(avx, avy)
        yoko, tate = check_bound(bb_rct)
        if not yoko:  # 横方向の判定
            vx *= -1
        if not tate:  # 縦方向の判定
            vy *= -1
        bb_vxy = (vx, vy)

        screen.blit(bb_img, bb_rct)  # 爆弾を表示させる
        if kk_rct.colliderect(bb_rct):
            gameover(screen)
            return
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
