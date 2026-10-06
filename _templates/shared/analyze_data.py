# Canonical EDA code, shared by template_python.ipynb and template_marimo.py via
# updater.py. Sections are delimited by '# === SECTION: name ===' markers and
# spliced individually into each template's placeholders. Not a standalone module:
# df/pd/plt/display are expected to already be available in the scope this gets
# spliced into.

# === SECTION: dropna ===
# drop columns that have no values
df.dropna(how="all", axis=1, inplace=True)

# === SECTION: shape_duplicates ===
print(
    f"The dataset has {df.shape[0]:,.0f} rows (observations) and {df.shape[1]:,.0f} columns (variables)."
)
print(f"There seem to be {df.duplicated().sum()} exact duplicates in the data.")

# === SECTION: info ===
df.info(memory_usage="deep", verbose=True)

# === SECTION: head ===
df.head()

# === SECTION: sample_transposed ===
# display a small random sample transposed in order to see all variables
df.sample(3).T

# === SECTION: describe_categorical ===
# describe non-numerical features
try:
    with pd.option_context("display.float_format", "{:,.2f}".format):
        display(df.describe(exclude="number"))
except ValueError:
    print("No categorical data in dataset.")

# === SECTION: describe_numeric ===
# describe numerical features
try:
    with pd.option_context("display.float_format", "{:,.2f}".format):
        display(df.describe(include="number"))
except ValueError:
    print("No numerical data in dataset.")

# === SECTION: missingno ===
# check missing values with missingno
# https://github.com/ResidentMario/missingno
import missingno as msno

msno.matrix(df, labels=True, sort="descending");

# === SECTION: histogram ===
# plot a histogram for each numerical feature
try:
    df.hist(bins=25, rwidth=0.9)
    plt.tight_layout()
    plt.show()
except ValueError:
    print("No numerical data to plot.")
