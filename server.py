#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI AD Director 后端服务
- 免费 API 中继（GemAI 免费模型 / IP 每日限流）
- 社区 Prompt 库（发布 / 搜索 / 点赞）
- 静态文件服务
复刻 塔罗牌/server.py 架构
"""

import json, os, hashlib, time
from datetime import date, datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.request, urllib.parse, ssl

# ============================================================
# 配置 —— 改这里！
# ============================================================
GEMAI_API_KEY = ""       # 你的 GemAI API Key。留空 = 免费中继关闭。
GEMAI_API_URL = "https://api.gemai.cc/v1/chat/completions"
FREE_MODEL = "gemini-2.0-flash"
FREE_DAILY_LIMIT = 3     # 每 IP 每天最多几次免费调用

PORT = int(os.environ.get("PORT", "8081"))
HOST = "0.0.0.0"
DATA_DIR = Path("_data")
DATA_DIR.mkdir(exist_ok=True)

PROMPTS_FILE = DATA_DIR / "prompts.json"
USERS_FILE = DATA_DIR / "users.json"
CATEGORIES_FILE = DATA_DIR / "categories.json"

# ============================================================
# 每日免费限制（IP + 日期哈希，与 Sorami 一致）
# ============================================================
def get_daily_key(ip: str) -> str:
    today = date.today().isoformat()
    return hashlib.sha256(f"{ip}:{today}:ad".encode()).hexdigest()[:12]

def check_free_quota(ip: str) -> dict:
    key = get_daily_key(ip)
    usage_file = DATA_DIR / f"ad_free_{key}.json"
    if usage_file.exists():
        data = json.loads(usage_file.read_text())
        used = data.get("count", 0)
        return {"free_remaining": max(0, FREE_DAILY_LIMIT - used),
                "free_used_today": used, "free_limit": FREE_DAILY_LIMIT}
    return {"free_remaining": FREE_DAILY_LIMIT, "free_used_today": 0,
            "free_limit": FREE_DAILY_LIMIT}

def mark_free_used(ip: str):
    key = get_daily_key(ip)
    usage_file = DATA_DIR / f"ad_free_{key}.json"
    current = check_free_quota(ip)
    usage_file.write_text(json.dumps({
        "ip_hash": key, "date": date.today().isoformat(),
        "count": current["free_used_today"] + 1,
    }, ensure_ascii=False))

# ============================================================
# Prompt 社区数据层
# ============================================================
def load_json(filepath: Path, default=None):
    if default is None:
        default = []
    if filepath.exists():
        try:
            return json.loads(filepath.read_text())
        except:
            return default
    return default

def save_json(filepath: Path, data):
    filepath.parent.mkdir(exist_ok=True)
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def seed_prompts():
    """首次启动：按 Tensor.art 分类体系，50 条社区验证 Prompt"""
    if PROMPTS_FILE.exists():
        return
    prompts = [
        # ============================================================
        # 1. 二次元动漫 (Anime) — Tensor.art 最大分类
        # ============================================================
        {"id":"p_seed_01","title":"赛璐璐动画截图","category":"二次元动漫","promptText":"masterpiece, best quality, anime screencap, cel-shaded animation style, sharp linework, flat vibrant colors, 2000s anime aesthetic, Kyoto Animation quality, emotional scene, wind blowing through hair, cherry blossom petals in air, school rooftop at sunset","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_02","title":"新海诚电影风","category":"二次元动漫","promptText":"Makoto Shinkai cinematic style, breathtaking sky, volumetric clouds, god rays piercing through cumulus, highly detailed background, lens flare, chromatic aberration, anime movie key visual, melancholic atmosphere, distant cityscape, train tracks stretching to horizon","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_03","title":"90年代赛璐璐OVA","category":"二次元动漫","promptText":"masterpiece, 1990s OVA anime style, hand-painted cel animation, visible film grain, slightly faded color palette, retro anime aesthetic, detailed mechanical design, dramatic shadows, bubble economy era Tokyo, VHS tape quality, nostalgic atmosphere","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_04","title":"Galgame视觉小说CG","category":"二次元动漫","promptText":"masterpiece, official art, (Galgame CG style:1.2), visual novel key illustration, dramatic backlighting, emotional character close-up, cherry blossom overlay, depth of field blur on background, teary eyes with light reflections, school uniform detail, text box space at bottom third","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_05","title":"Pixiv人气插画风","category":"二次元动漫","promptText":"masterpiece, trending on pixiv, semi-realistic anime illustration, detailed hair strands, soft skin subsurface scattering, sparkle particle effects, light bokeh circles, pastel color harmony, intricate eye highlights with 3 layers of reflection, delicate fingers, wind-swept composition","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_06","title":"地雷系/量産型","category":"二次元动漫","promptText":"jirai kei fashion, landmine type girl, dark cute aesthetic, pink and black color palette, teary doe eyes, lace choker, platform shoes, Shinjuku night background, mental health chic, soft focus, social media selfie angle, Japanese street snap style","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 2. 写实摄影 (Realistic Photography)
        # ============================================================
        {"id":"p_seed_07","title":"胶片人像写真","category":"写实摄影","promptText":"RAW color photograph, cinematic portrait, Kodak Portra 400 film stock, natural window light, shallow depth of field f/1.4, creamy bokeh background, soft skin texture with visible pores, authentic expression, golden hour rim light, analog film grain, hasselblad medium format","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_08","title":"赛博朋克夜街拍","category":"写实摄影","promptText":"cyberpunk street photography, rain-slicked asphalt reflecting neon signs, steam rising from subway vents, Blade Runner aesthetic, cinematic wide shot, cyan and magenta neon rim lighting, wet pavement, crowded Shibuya crossing at night, 35mm wide angle lens, high contrast, blade runner color grade","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_09","title":"时尚杂志大片","category":"写实摄影","promptText":"high fashion editorial photography, Vogue magazine cover quality, professional studio lighting setup, dramatic key light with soft fill, model with striking pose, designer clothing detail, crisp fabric texture, bold makeup look, seamless white background, medium format digital, 80MP detail","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_10","title":"日系生活感写真","category":"写实摄影","promptText":"Japanese lifestyle photography, cozy sunlit apartment interior, cream and beige tones, morning light through sheer curtains, minimal Scandinavian-Japanese hybrid decor, woman reading by window, cup of steaming coffee, relaxed candid moment, fujifilm classic negative film simulation, warm white balance","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_11","title":"美食商业摄影","category":"写实摄影","promptText":"professional food photography, overhead flat lay composition, artisan ramen bowl, chopsticks lifting noodles, steam wisps, dramatic side lighting, rich color saturation, glossy egg yolk texture, scattered fresh herbs as garnish, dark moody background, 100mm macro lens, Michelin guide quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 3. 人物角色 (Character & Portrait)
        # ============================================================
        {"id":"p_seed_12","title":"游戏角色立绘","category":"人物角色","promptText":"character design sheet, gacha game SSR character, full body standing pose, elaborate fantasy outfit with gold trim and flowing cape, detailed weapon design, confident expression, dramatic cape flutter, character introduction screen composition, front view, clean white background for easy cutout, mobile game key visual quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_13","title":"赛博朋克角色","category":"人物角色","promptText":"cyberpunk character portrait, neon-lit face, holographic visor over one eye, chrome cybernetic enhancements on cheek and neck, short asymmetrical haircut with LED streaks, leather jacket with circuit patterns, rainy night city reflected in visor, moody expression, purple and teal duotone lighting, highly detailed skin pores, cyberpunk 2077 quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_14","title":"奇幻精灵角色","category":"人物角色","promptText":"fantasy elf character portrait, ethereal beauty, pointed ears peeking through flowing silver hair, luminescent skin with subtle glow, jewel-toned emerald eyes with intricate iris detail, forest dappled light through leaves, delicate floral crown, gossamer fabric clothing, magical floating dust particles, Dungeons & Dragons inspired, oil painting quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_15","title":"日系美少女商业立绘","category":"人物角色","promptText":"bishoujo character introduction screen, Japanese mobile game key visual, waist-up portrait, painterly skin rendering with subsurface scattering, luminous anime eyes with multi-layer highlights, natural cheek flush, soft lip gloss, shallow depth of field, warm interior lighting, framed by cherry blossom branches, commercial illustration quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_16","title":"写实人物肖像","category":"人物角色","promptText":"hyperrealistic portrait photograph, middle-aged man with weathered face, every wrinkle and pore visible, intense gaze directly at camera, dramatic Rembrandt lighting, dark moody background, sharp focus on eyes, 85mm portrait lens f/1.2, national geographic portrait contest winner, emotional depth, dignified expression","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 4. 插画设计 (Illustration & Concept Art)
        # ============================================================
        {"id":"p_seed_17","title":"厚涂概念艺术","category":"插画设计","promptText":"digital oil painting, thick impasto brushstrokes, fantasy landscape, ruined ancient temple overgrown with bioluminescent flora, epic scale, atmospheric perspective, god rays breaking through dense jungle canopy, vibrant teal and gold color palette, Craig Mullins inspired, ArtStation featured, concept art quality, 8k resolution","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_18","title":"水彩手绘风","category":"插画设计","promptText":"watercolor illustration, wet-on-wet technique, botanical study of peony flowers, delicate pink and crimson washes, visible paper texture, ink line accents, artistic negative space, floating composition, Japanese botanical illustration style, soft color bleeding at edges, handmade craft feel, white background","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_19","title":"浮世绘现代改编","category":"插画设计","promptText":"ukiyo-e woodblock print style, modern Tokyo reinterpreted, Hokusai-inspired great wave with Shibuya scramble crossing, traditional Japanese color palette of indigo and vermilion, visible wood grain texture, 葛飾北斎 meets cyberpunk, decorative cloud patterns, kanji calligraphy in margin, washi paper texture overlay","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_20","title":"美式漫画封面","category":"插画设计","promptText":"american comic book cover art, dynamic superhero pose, forced perspective from below, bold ink lines with halftone dot shading, vibrant primary colors, speed lines and action burst effects, dramatic foreshortening, Marvel comics 1990s style, title space at top, corner box with character headshot, newsprint texture","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 5. 科幻赛博 (Sci-Fi & Cyberpunk)
        # ============================================================
        {"id":"p_seed_21","title":"赛博城市全景","category":"科幻赛博","promptText":"sprawling cyberpunk metropolis, flying vehicles between towering neon-lit skyscrapers, holographic advertisements in air, perpetual rain, steam from street level, multi-level city with elevated highways, purple and orange neon dominant, Blade Runner 2049 aesthetic, cinematic wide angle, volumetric fog, highly detailed cityscape","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_22","title":"星际飞船内部","category":"科幻赛博","promptText":"spaceship interior corridor, sleek sci-fi design, white and chrome surfaces with blue LED accent lighting, holographic control panels, viewport showing distant nebula, NASA-punk aesthetic meets Apple design language, clean minimal lines, zero-gravity floating interface elements, ambient occlusion, ray-tracing quality, 8k","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_23","title":"末日废土","category":"科幻赛博","promptText":"post-apocalyptic wasteland, rusted vehicle wreckage in desert, lone survivor in weathered gas mask and patched leather, sand storm approaching on horizon, orange dust haze, Mad Max aesthetic, wide cinematic composition, gritty texture, bleached bone fragments scattered, vulture circling overhead, dramatic sky, film grain","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_24","title":"机甲格纳库","category":"科幻赛博","promptText":"giant mecha hangar, towering 50-meter robot in maintenance bay, sparks from welding drones, crew scaffolding around shoulders, dramatic low-angle shot emphasizing mech scale, industrial yellow warning lights, steam vents, Gundam UC aesthetic, detailed mechanical joints and hydraulic pistons, anime mecha art style, epic atmosphere","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 6. 自然风景 (Landscape & Nature)
        # ============================================================
        {"id":"p_seed_25","title":"极光雪山","category":"自然风景","promptText":"epic landscape photography, snow-capped mountain peak under dancing aurora borealis, green and purple northern lights reflecting in frozen lake, starry night sky with Milky Way, pristine untouched wilderness, long exposure, ultra wide angle 14mm, national geographic quality, crisp air, foreground ice crystals detailed","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_26","title":"日式庭院","category":"自然风景","promptText":"traditional Japanese zen garden, carefully raked gravel patterns, moss-covered stone lantern, maple tree with autumn red leaves, koi pond with gentle ripples, bamboo water fountain, morning mist, soft diffused light, Kyoto temple grounds, peaceful contemplative atmosphere, ikebana flower arrangement in foreground, 4k","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_27","title":"奇幻森林","category":"自然风景","promptText":"enchanted forest, bioluminescent mushrooms glowing blue and purple, ancient twisted oak trees with faces in bark, fairy lights floating between branches, moss-covered stone path leading deeper into woods, volumetric god rays through canopy, magical atmosphere, Studio Ghibli nature aesthetic, dappled light, fireflies, whimsical","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 7. 游戏设计 (Game Design)
        # ============================================================
        {"id":"p_seed_28","title":"像素风场景","category":"游戏设计","promptText":"pixel art game background, 16-bit RPG town, cozy medieval village with cobblestone paths, timber-framed houses with smoking chimneys, pixel-perfect dithering, limited 64 color palette, SNES-era aesthetic, parallax scrolling layers, top-down RPG perspective, Stardew Valley meets Chrono Trigger","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_29","title":"等距游戏地图","category":"游戏设计","promptText":"isometric game environment, fantasy floating islands connected by rope bridges, crystal mines with glowing gems embedded in rocks, waterfalls cascading off island edges into clouds below, diorama style, clean game-ready art, mobile strategy game aesthetic, bright saturated colors, cartoon rendering style, Clash of Clans meets Monument Valley","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_30","title":"武器道具设计","category":"游戏设计","promptText":"game asset concept art, legendary sword design, ornate golden hilt with embedded ruby, damascus steel blade pattern with subtle blue glow runes, leather-wrapped grip, weapon display stand with velvet, front view orthographic, RPG inventory item quality, detailed craftsmanship, diablo-style dark fantasy aesthetic, white background for sprite extraction","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_31","title":"低多边形3D场景","category":"游戏设计","promptText":"low poly 3D game environment, stylized autumn forest camp, geometric pine trees in orange and red, polygonal campfire with particle flame, flat shaded tent with supplies scattered, isometric view, clean unlit texture style, vibrant pastel color palette, Monument Valley meets A Short Hike aesthetic, mobile game ready","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 8. 空间建筑 (Architecture & Interior)
        # ============================================================
        {"id":"p_seed_32","title":"极简主义室内","category":"空间建筑","promptText":"minimalist interior design, Japandi style living room, warm oak floors, cream linen sofa, large potted monstera plant, floor-to-ceiling windows with diffused morning light, neutral beige and soft green palette, architectural digest quality, uncluttered space, natural materials, shadow play on textured wall, 8k architectural photography","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_33","title":"赛博咖啡厅","category":"空间建筑","promptText":"cyberpunk coffee shop interior, neon menu signs in Japanese, exposed concrete walls with holographic art projections, LED strip lighting under tables, robot barista with articulated arms, rain-streaked window looking out to neon city, steam from espresso machine, cozy corner booth with vintage synthwave aesthetic, blade runner meets hipster cafe","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_34","title":"空中花园建筑","category":"空间建筑","promptText":"futuristic vertical garden skyscraper, terraced architecture with cascading greenery, hanging gardens of Babylon reimagined, glass and living wall facade, drone delivery landing pads, solar panel integration, golden hour sun casting long shadows, sustainable architecture concept, parametric design, architectural visualization, 8k render","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 9. 抽象艺术 (Abstract & Artistic)
        # ============================================================
        {"id":"p_seed_35","title":"极简几何抽象","category":"抽象艺术","promptText":"minimalist abstract composition, Bauhaus geometric forms, primary colors red blue yellow on cream background, clean hard edges, asymmetrical balance, mid-century modern aesthetic, Mondrian meets Josef Albers, gallery wall quality, flat vector style, negative space utilization, graphic design poster, museum print quality","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_36","title":"故障艺术","category":"抽象艺术","promptText":"glitch art, corrupted digital signal aesthetic, portrait fragmented into RGB channel displacement, horizontal scan lines, VHS tracking error artifacts, datamoshing effect, neon purple and cyan color bleed, retro CRT monitor distortion, vaporwave meets brutalist design, album cover quality, nostalgic technology failure beauty","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 10. 光影构图 (Lighting & Composition)
        # ============================================================
        {"id":"p_seed_37","title":"Rembrandt三角光","category":"光影构图","promptText":"masterpiece, Rembrandt lighting setup, classic triangular light patch under eye on shadowed cheek, single key light from 45 degrees, deep rich shadows, dark background absorbs into void, sculptural lighting reveals facial structure, classical painting aesthetic, dramatic chiaroscuro, timeless portrait mood","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_38","title":"霓虹双色光","category":"光影构图","promptText":"cyberpunk rim lighting, dual-color setup, cyan key light from left, magenta fill from right, subject face split by complementary neon, volumetric fog catching light beams, film noir meets synthwave, dramatic shadows, wet surfaces reflecting colored light, Blade Runner lighting scheme","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_39","title":"黄金时刻逆光","category":"光影构图","promptText":"golden hour backlighting, subject silhouette rim-lit by warm sunset, hair glowing like halo, lens flare artifacts, shallow depth of field with bokeh circles, warm amber and rose color palette, nostalgic summer evening mood, natural reflectors bouncing warm light back onto subject, cinematic anamorphic lens, Terrence Malick film aesthetic","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_40","title":"Dutch Angle张力构图","category":"光影构图","promptText":"Dutch angle composition, 12 degree tilted frame, dynamic diagonal tension, subject centered but world tilted, psychological unease conveyed through framing, converging perspective lines pulling toward off-center vanishing point, dramatic wide angle lens distortion, thriller movie cinematography, Hitchcock inspired","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_41","title":"框中框构图","category":"光影构图","promptText":"frame within a frame composition, subject seen through arched doorway, natural foreground framing element, deep layering with foreground doorframe (dark), midground subject (lit), background window (bright), voyeuristic perspective, renaissance painting composition technique, architectural framing, depth staging, Kubrick one-point perspective","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 11. 产品商业 (Product & Commercial)
        # ============================================================
        {"id":"p_seed_42","title":"香水产品大片","category":"产品商业","promptText":"luxury perfume bottle product photography, crystal glass faceted bottle, golden liquid inside, dramatic spotlight on product, dark moody background with smoke swirls, water droplets on glass surface, high-end cosmetic advertising quality, intricate cap design detail, reflection on polished black marble surface, 100mm macro, 8k commercial","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_43","title":"运动鞋广告","category":"产品商业","promptText":"sneaker commercial photography, limited edition running shoes floating mid-air, dynamic action freeze, dust particles suspended around shoes, dramatic side lighting revealing fabric texture, neon accent on sole, urban rooftop background at blue hour, Nike ad campaign aesthetic, motion blur on background elements, product hero shot","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_44","title":"科技产品渲染","category":"产品商业","promptText":"Apple-style product render, smartphone floating at 30 degree angle, clean white infinite background, soft studio lighting with gradient reflection on screen, precise edge highlights revealing aluminum frame, minimal shadow, product design award photography, hyperrealistic 3D render quality, sleek and premium feel","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 12. 时尚穿搭 (Fashion)
        # ============================================================
        {"id":"p_seed_45","title":"街头潮流穿搭","category":"时尚穿搭","promptText":"street fashion editorial, Harajuku-inspired layered outfit, oversized vintage band tee under cropped leather jacket, wide-leg cargo pants, chunky platform sneakers, colorful accessories stacking, confident pose in Shibuya back alley, natural daylight, fashion blogger aesthetic, full body shot, Z世代 style","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_46","title":"高级定制礼服","category":"时尚穿搭","promptText":"haute couture gown, runway fashion, dramatic floor-length tulle dress with crystal embroidery, cathedral train, museum lighting setup, rotating display platform, fashion week backstage quality, intricate beadwork detail macro visible, elegant silhouette, Vogue editorial, soft ethereal lighting, mannequin display","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 13. 二次元场景 (Anime Background Art)
        # ============================================================
        {"id":"p_seed_47","title":"动画美术背景","category":"二次元动漫","promptText":"anime background art, detailed classroom interior after school, warm golden hour light streaming through windows, chalk dust floating in sunbeams, empty desks with scattered notebooks, cherry blossoms visible outside window, Makoto Shinkai level background detail, painterly matte painting, Studio Ghibli background art quality, serene atmosphere","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_48","title":"蒸汽波动漫loop","category":"二次元动漫","promptText":"vaporwave anime aesthetic, 80s Japanese city pop album cover, marble bust with neon grid overlay, palm tree silhouette against gradient sunset, VHS tracking lines, Japanese text overlay in bold font, retro CRT scanlines, purple and pink gradient, nostalgic 未来感, lo-fi hip hop visual","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},

        # ============================================================
        # 14. 动物 (Animals)
        # ============================================================
        {"id":"p_seed_49","title":"猫的肖像","category":"写实摄影","promptText":"cat portrait photography, majestic Maine Coon with flowing fur, piercing green eyes with catchlights, whiskers in sharp detail, dramatic side lighting on fur texture, black background, regal pose, national geographic animal portrait quality, 85mm portrait lens, shallow depth of field, wild elegance","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
        {"id":"p_seed_50","title":"幻想生物设计","category":"插画设计","promptText":"fantasy creature concept art, small dragon-cat hybrid, iridescent scales transitioning to fur, large curious eyes, sitting on ancient wizard tome, candlelight illuminating the scene, warm magical glow, creature design sheet, Dungeons & Dragons monster manual style, leather texture on book cover, copper bookmark detail","authorId":"system","displayName":"系统库","createdAt":"2026-06-01T00:00:00","public":True,"likes":0,"likedBy":[],"reports":[]},
    ]
    save_json(PROMPTS_FILE, prompts)
    print(f"[Seed] 已创建 {len(prompts)} 条种子 Prompt")

def update_categories():
    """每次操作后刷新 categories.json"""
    prompts = load_json(PROMPTS_FILE, [])
    cat_counts = {}
    for p in prompts:
        cat = p.get("category", "未分类")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    cats = [{"slug": c, "displayName": c, "count": n} for c, n in cat_counts.items()]
    # 保持稳定排序
    cats.sort(key=lambda x: x["displayName"])
    save_json(CATEGORIES_FILE, cats)

def get_stats() -> dict:
    prompts = load_json(PROMPTS_FILE, [])
    users = load_json(USERS_FILE, [])
    total_likes = sum(p.get("likes", 0) for p in prompts)
    return {
        "total_prompts": len(prompts),
        "total_users": len(users),
        "total_likes": total_likes,
        "categories": len({p.get("category") for p in prompts}),
    }

# ============================================================
# HTTP 服务器
# ============================================================
class ADHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    # ── GET ──
    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/status":
            ip = self.client_address[0]
            quota = check_free_quota(ip)
            self._json_response({
                **quota,
                "relay_enabled": bool(GEMAI_API_KEY),
                "free_model": FREE_MODEL,
            })
            return

        if path == "/api/prompts":
            self._handle_list_prompts()
            return

        if path == "/api/categories":
            cats = load_json(CATEGORIES_FILE, [])
            self._json_response({"categories": cats})
            return

        if path == "/api/stats":
            self._json_response(get_stats())
            return

        # 默认：静态文件
        super().do_GET()

    # ── POST ──
    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/chat":
            self._handle_chat()
            return

        if path == "/api/prompts":
            self._handle_create_prompt()
            return

        if path.endswith("/like"):
            # /api/prompts/<id>/like
            prompt_id = path.replace("/api/prompts/", "").replace("/like", "")
            self._handle_toggle_like(prompt_id)
            return

        if path.endswith("/report"):
            # /api/prompts/<id>/report
            prompt_id = path.replace("/api/prompts/", "").replace("/report", "")
            self._handle_report(prompt_id)
            return

        self._json_response({"error": "Not found"}, 404)

    # ── 免费中继 ──
    def _handle_chat(self):
        ip = self.client_address[0]

        if not GEMAI_API_KEY:
            self._json_response({
                "error": "relay_disabled",
                "message": "免费中继未启用。请填写你的 API Key 或联系管理员。"
            }, 503)
            return

        quota = check_free_quota(ip)
        if quota["free_remaining"] <= 0:
            self._json_response({
                "error": "daily_limit",
                "message": f"今日免费额度已用完（{FREE_DAILY_LIMIT}/{FREE_DAILY_LIMIT}）。明天再来，或填写你自己的 API Key 解锁无限次！",
                "free_remaining": 0,
            }, 429)
            return

        # 读取请求体
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            self._json_response({"error": "Invalid JSON"}, 400)
            return

        # 强制免费模型
        data["model"] = FREE_MODEL
        data["max_tokens"] = data.get("max_tokens", 300)
        data["temperature"] = data.get("temperature", 0.3)

        try:
            req = urllib.request.Request(
                GEMAI_API_URL,
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GEMAI_API_KEY}",
                }
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            mark_free_used(ip)
            remaining = check_free_quota(ip)
            self._json_response({
                **result,
                "free_remaining": remaining["free_remaining"],
                "free_model": FREE_MODEL,
            })
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")[:200]
            except:
                pass
            self._json_response({
                "error": "relay_error",
                "message": f"上游 API 错误 (HTTP {e.code}): {err_body}",
            }, 502)
        except Exception as e:
            self._json_response({
                "error": "relay_error",
                "message": f"网络错误: {str(e)}",
            }, 502)

    # ── Prompt 列表 / 搜索 ──
    def _handle_list_prompts(self):
        params = urllib.parse.parse_qs(
            self.path.split("?")[1] if "?" in self.path else ""
        )
        search = params.get("search", [""])[0].strip().lower()
        category = params.get("category", [""])[0].strip()
        sort = params.get("sort", ["newest"])[0].strip()
        limit_str = params.get("limit", ["50"])[0]
        try:
            limit = int(limit_str)
        except:
            limit = 50

        prompts = load_json(PROMPTS_FILE, [])

        # 搜索过滤
        if search:
            prompts = [
                p for p in prompts
                if search in p.get("title", "").lower()
                or search in p.get("promptText", "").lower()
                or search in p.get("category", "").lower()
            ]

        # 分类过滤
        if category and category != "全部":
            prompts = [p for p in prompts if p.get("category") == category]

        # 排序
        if sort == "popular":
            prompts.sort(key=lambda p: p.get("likes", 0), reverse=True)
        else:  # newest
            prompts.sort(key=lambda p: p.get("createdAt", ""), reverse=True)

        total = len(prompts)
        prompts = prompts[:limit]

        # Filter: only show public prompts + user's own private prompts
        # Also hide prompts with >=3 reports unless owner is viewing
        user_id = params.get("userId", [""])[0].strip()
        if user_id:
            prompts = [p for p in prompts if (p.get("public", True) or p.get("authorId") == user_id) and (len(p.get("reports",[])) < 3 or p.get("authorId") == user_id)]
        else:
            prompts = [p for p in prompts if p.get("public", True) and len(p.get("reports",[])) < 3]
        total = len(prompts)
        prompts = prompts[:limit]

        self._json_response({"prompts": prompts, "total": total})

    # ── 发布 Prompt ──
    def _handle_create_prompt(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            self._json_response({"error": "Invalid JSON"}, 400)
            return

        title = (data.get("title") or "").strip()
        category_ = (data.get("category") or "未分类").strip()
        prompt_text = (data.get("promptText") or "").strip()
        user_id = (data.get("userId") or "anonymous").strip()
        display_name = (data.get("displayName") or "匿名用户").strip()
        is_public = data.get("public", True)  # default public

        if not title or not prompt_text:
            self._json_response({"error": "标题和 Prompt 内容不能为空"}, 400)
            return
        if len(title) > 100:
            self._json_response({"error": "标题最长 100 字"}, 400)
            return
        if len(prompt_text) > 5000:
            self._json_response({"error": "Prompt 最长 5000 字"}, 400)
            return

        # 去重：同用户同标题不重复提交
        prompts = load_json(PROMPTS_FILE, [])
        for p in prompts:
            if p.get("authorId") == user_id and p.get("title") == title:
                self._json_response({"error": "你已经发布过同名 Prompt 了"}, 409)
                return

        prompt = {
            "id": f"p_{int(time.time()*1000)}_{os.urandom(2).hex()}",
            "title": title,
            "category": category_,
            "promptText": prompt_text,
            "authorId": user_id,
            "displayName": display_name,
            "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "public": is_public,
            "likes": 0,
            "likedBy": [],
            "reports": [],
        }
        prompts.append(prompt)
        save_json(PROMPTS_FILE, prompts)

        # 更新用户记录
        users = load_json(USERS_FILE, [])
        if not any(u.get("userId") == user_id for u in users):
            users.append({
                "userId": user_id,
                "displayName": display_name,
                "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            })
            save_json(USERS_FILE, users)

        update_categories()
        self._json_response({"prompt": prompt}, 201)

    # ── 点赞 / 取消 ──
    def _handle_toggle_like(self, prompt_id: str):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            self._json_response({"error": "Invalid JSON"}, 400)
            return

        user_id = (data.get("userId") or "").strip()
        if not user_id:
            self._json_response({"error": "需要 userId"}, 400)
            return

        prompts = load_json(PROMPTS_FILE, [])
        for p in prompts:
            if p.get("id") == prompt_id:
                liked_by = p.get("likedBy", [])
                if user_id in liked_by:
                    liked_by.remove(user_id)
                    p["likes"] = max(0, p.get("likes", 1) - 1)
                    action = "unliked"
                else:
                    liked_by.append(user_id)
                    p["likes"] = p.get("likes", 0) + 1
                    action = "liked"
                p["likedBy"] = liked_by
                save_json(PROMPTS_FILE, prompts)
                # 不更新 categories（count 不变）
                self._json_response({
                    "action": action,
                    "likes": p["likes"],
                })
                return

        self._json_response({"error": "Prompt not found"}, 404)

    # ── 举报 Prompt ──
    def _handle_report(self, prompt_id: str):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            self._json_response({"error": "Invalid JSON"}, 400)
            return

        user_id = (data.get("userId") or "").strip()
        reason = (data.get("reason") or "").strip()
        valid_reasons = ["暴力/血腥内容", "色情/NSFW内容", "与Prompt无关", "广告/垃圾信息", "其他"]
        if not user_id:
            self._json_response({"error": "需要 userId"}, 400)
            return
        if reason not in valid_reasons:
            self._json_response({"error": "请选择有效举报理由"}, 400)
            return

        prompts = load_json(PROMPTS_FILE, [])
        for p in prompts:
            if p.get("id") == prompt_id:
                reports = p.get("reports", [])
                # 同一用户不重复举报同一条
                if any(r.get("reporterId") == user_id for r in reports):
                    self._json_response({"error": "你已经举报过这条 Prompt 了"}, 409)
                    return
                reports.append({
                    "reporterId": user_id,
                    "reason": reason,
                    "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                })
                p["reports"] = reports
                save_json(PROMPTS_FILE, prompts)
                self._json_response({
                    "action": "reported",
                    "reportCount": len(reports),
                    "hidden": len(reports) >= 3,
                })
                return

        self._json_response({"error": "Prompt not found"}, 404)

    # ── 工具方法 ──
    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    seed_prompts()
    update_categories()
    cat_count = len(load_json(CATEGORIES_FILE, []))
    prompt_count = len(load_json(PROMPTS_FILE, []))

    print("=" * 50)
    print("🎬 AI AD Director Server v31")
    print(f"   http://{HOST}:{PORT}")
    print()
    print("   配置检查:")
    if GEMAI_API_KEY:
        print(f"   ✅ 免费中继已启用 ({FREE_MODEL} · 每 IP {FREE_DAILY_LIMIT} 次/天)")
    else:
        print("   ⚠️  免费中继未启用（GEMAI_API_KEY 为空）")
    print(f"   📚 Prompt 社区: {prompt_count} 条 · {cat_count} 分类")
    print("=" * 50)

    server = ThreadingHTTPServer((HOST, PORT), ADHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.server_close()
