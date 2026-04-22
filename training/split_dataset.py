import random
import shutil
from pathlib import Path

random.seed(42)

SOURCE_DIR = Path("dataset_raw")
TARGET_DIR = Path("dataset_split")

TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}


def clear_target():
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)


def prepare_folders(classes):
    for split in ["train", "val", "test"]:
        for class_name in classes:
            (TARGET_DIR / split / class_name).mkdir(parents=True, exist_ok=True)


def split_files(files):
    random.shuffle(files)
    n = len(files)

    train_end = int(n * TRAIN_RATIO)
    val_end = train_end + int(n * VAL_RATIO)

    train_files = files[:train_end]
    val_files = files[train_end:val_end]
    test_files = files[val_end:]

    return train_files, val_files, test_files


def copy_files(files, split_name, class_name):
    for file_path in files:
        destination = TARGET_DIR / split_name / class_name / file_path.name
        shutil.copy2(file_path, destination)


def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Папка {SOURCE_DIR} не найдена")

    clear_target()

    classes = [d.name for d in SOURCE_DIR.iterdir() if d.is_dir()]
    if not classes:
        raise ValueError("Не найдены папки классов в dataset_raw")

    prepare_folders(classes)

    for class_name in classes:
        class_dir = SOURCE_DIR / class_name
        files = [
            f for f in class_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
        ]

        if len(files) == 0:
            print(f"Класс '{class_name}' пустой")
            continue

        train_files, val_files, test_files = split_files(files)

        copy_files(train_files, "train", class_name)
        copy_files(val_files, "val", class_name)
        copy_files(test_files, "test", class_name)

        print(
            f"{class_name}: "
            f"train={len(train_files)}, "
            f"val={len(val_files)}, "
            f"test={len(test_files)}"
        )

    print("Разбиение датасета завершено.")


if __name__ == "__main__":
    main()