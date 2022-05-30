"""
Use this bot to label videofiles
"""
import datetime
import json
import logging
import os
import random
from hashlib import md5
from pathlib import Path

import yaml
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.input_file import InputFile
from aiogram.utils.callback_data import CallbackData


# Functions

DEBUG = os.environ.get("DEBUG", False)


def load_yaml(path: Path):
    with open(path, "r") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def today():
    return datetime.datetime.today().strftime("%m%d")


formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")


def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def get_hash(fpath):
    """
    /Users/ko/Downloads/gifs_to_label/March/February 28 — March 6/GAMID/justin_biber_idea.mp4 ->
        March/February 28 — March 6/GAMID/justin_biber_idea.mp4 ->
            fc7a0dbefd15bb091e54cccd654cddba
    """
    return md5(fpath.as_posix().replace(BASE_DIR, "").encode("utf-8")).hexdigest()


logger_results = setup_logger("logger_results", "label-results.log")

tokens = load_yaml(Path(__file__).parent / "tokens.yaml")


BASE_DIR = None
if BASE_DIR is None:
    raise ValueError("Please set BASE_DIR to the directory where the videos are stored (line 62")

if not Path(BASE_DIR).exists():
    raise ValueError(f"{BASE_DIR} doesn't exist")


API_TOKEN: str = os.environ.get("TELEGRAM_TOKEN", tokens.get(Path(__file__).stem))
VIDEOS = list(Path(BASE_DIR).rglob("**/*.mp4"))
VIDEO_NAMES = {get_hash(p): p.as_posix() for p in VIDEOS}

json.dump(VIDEO_NAMES, open(BASE_DIR + f"files-{today()}.json", "w"))
assert len(VIDEO_NAMES) == len(VIDEOS)

logging.basicConfig(filename="label-bot.log", level=logging.DEBUG)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

call_back_info = CallbackData("prefix", "text", "video")


@dp.message_handler(commands="start")
async def start_cmd_handler(message: types.Message):
    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
    text_and_data = (("start", "start"),)
    # in real life for the callback_data the callback data factory should be used
    # here the raw string is used for the simplicity
    row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)

    keyboard_markup.row(*row_btns)
    await message.reply("Let's start!", reply_markup=keyboard_markup)


@dp.callback_query_handler(text="start")
@dp.callback_query_handler(text="no")
@dp.callback_query_handler(text="yes")
@dp.callback_query_handler(text="isok")
@dp.callback_query_handler(
    call_back_info.filter(text="yes") | call_back_info.filter(text="no") | call_back_info.filter(text="isok")
)
async def inline_kb_answer_callback_handler(query: types.CallbackQuery):
    answer_data = query.data
    # always answer callback queries, even if you have nothing to say
    msg = f"{query.from_user.username} answered with {answer_data!r}"
    await query.answer(msg)
    print(msg)  # stdout

    # callback results
    if answer_data.split(":")[0] == "start":
        pass
    else:
        cb_text = call_back_info.parse(answer_data)["text"]
        cb_video = call_back_info.parse(answer_data)["video"]
        cb_username = query.from_user.username
        MSG = f"{cb_text} {cb_video} {cb_username}"
        logger_results.info(MSG)

    v_key, v_val = random.sample(VIDEO_NAMES.items(), 1)[0]
    text_and_data = (
        ("👍", ("yes", v_key)),
        ("😐", ("isok", v_key)),
        ("👎", ("no", v_key)),
    )

    row_btns = (
        types.InlineKeyboardButton(text, callback_data=call_back_info.new(*data)) for text, data in text_and_data
    )

    keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
    keyboard_markup.row(*row_btns)

    file = InputFile(v_val)

    await bot.send_video(
        query.from_user.id,
        video=file,
        caption="Video to label",
        reply_markup=keyboard_markup,
    )


@dp.message_handler()
async def handle_message(message):
    await message.answer("🐶 Please run /start command 🐶")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
